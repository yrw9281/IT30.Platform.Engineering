from datetime import datetime, timezone
import re
from typing import Any

Json = dict[str, Any]
API_VERSION = "platform.example.io/v1alpha1"
LABEL = "platform.example.io/microservice-uid"


class InvalidSpec(ValueError):
    pass


class OwnershipConflict(ValueError):
    pass


def desired_resources(cr: Json) -> tuple[Json, Json]:
    meta, spec = cr["metadata"], cr.get("spec", {})
    image, port = spec.get("image"), spec.get("port")
    if not isinstance(image, str) or not image.strip():
        raise InvalidSpec("spec.image must be a non-empty string")
    if type(port) is not int or not 1 <= port <= 65535:
        raise InvalidSpec("spec.port must be an integer between 1 and 65535")
    name, namespace, uid = meta["name"], meta["namespace"], meta["uid"]
    if len(name) > 63 or not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", name):
        raise InvalidSpec("metadata.name must be a DNS label of at most 63 characters")
    labels = {"app": name, LABEL: uid}
    owner = {"apiVersion": API_VERSION, "kind": "Microservice", "name": name,
             "uid": uid, "controller": True, "blockOwnerDeletion": False}
    metadata = {"name": name, "namespace": namespace, "labels": labels,
                "ownerReferences": [owner]}
    container = {
        "name": name, "image": image, "imagePullPolicy": "IfNotPresent",
        "ports": [{"name": "http", "containerPort": port}],
        "env": [
            {"name": "ASPNETCORE_URLS", "value": f"http://+:{port}"},
            {"name": "OTEL_SERVICE_NAME", "value": name},
            {"name": "OTEL_SERVICE_VERSION", "value": image},
            {"name": "DEPLOYMENT_ENVIRONMENT", "value": "development"},
            {"name": "OTEL_EXPORTER_OTLP_ENDPOINT",
             "value": "http://otel-collector.observability.svc:4317"},
        ],
        "readinessProbe": {"httpGet": {"path": "/health/ready", "port": "http"}},
        "livenessProbe": {"httpGet": {"path": "/health/live", "port": "http"},
                          "initialDelaySeconds": 10},
        "resources": {"requests": {"cpu": "25m", "memory": "128Mi"},
                      "limits": {"cpu": "500m", "memory": "256Mi"}},
    }
    deployment = {
        "apiVersion": "apps/v1", "kind": "Deployment", "metadata": metadata,
        "spec": {
            "replicas": 2, "progressDeadlineSeconds": 120,
            "selector": {"matchLabels": {"app": name}},
            "template": {"metadata": {"labels": labels},
                         "spec": {"automountServiceAccountToken": False,
                                  "tolerations": [{
                                      "key": "node-role.kubernetes.io/control-plane",
                                      "operator": "Exists", "effect": "NoSchedule",
                                  }],
                                  "containers": [container]}},
        },
    }
    service = {
        "apiVersion": "v1", "kind": "Service", "metadata": metadata,
        "spec": {"type": "ClusterIP", "selector": {"app": name},
                 "ports": [{"name": "http", "port": port, "targetPort": "http"}]},
    }
    return deployment, service


def check_owner(current: Json, cr: Json) -> None:
    owners = current["metadata"].get("ownerReferences", [])
    if not any(owner.get("uid") == cr["metadata"]["uid"]
               and owner.get("apiVersion") == API_VERSION
               and owner.get("kind") == "Microservice"
               and owner.get("controller") is True for owner in owners):
        raise OwnershipConflict(
            f'{current["kind"]}/{current["metadata"]["name"]} is not owned by this CR')


def contains(current: Any, desired: Any) -> bool:
    if isinstance(desired, dict):
        return isinstance(current, dict) and all(
            key in current and contains(current[key], value)
            for key, value in desired.items())
    if isinstance(desired, list):
        return isinstance(current, list) and len(current) == len(desired) and all(
            contains(actual, target) for actual, target in zip(current, desired))
    return current == desired


def health(deployment: Json, slices: list[Json], pods: list[Json],
           image: str) -> tuple[bool, bool, str, str]:
    status = deployment.get("status", {})
    if status.get("observedGeneration", 0) < deployment["metadata"]["generation"]:
        return False, False, "Reconciling", "Deployment controller has not observed this version"
    for pod in pods:
        for container in pod.get("spec", {}).get("containers", []):
            if container["image"] != image:
                continue
            for observed in pod.get("status", {}).get("containerStatuses", []):
                if observed["name"] != container["name"]:
                    continue
                waiting = observed.get("state", {}).get("waiting", {})
                if waiting.get("reason") in {
                    "ErrImagePull", "ImagePullBackOff", "InvalidImageName",
                    "CrashLoopBackOff", "CreateContainerConfigError",
                }:
                    return False, True, waiting["reason"], "Inspect managed Pod events and logs"
    if any(condition.get("type") == "Progressing"
           and condition.get("status") == "False"
           and condition.get("reason") == "ProgressDeadlineExceeded"
           for condition in status.get("conditions", [])):
        return False, True, "ProgressDeadlineExceeded", "Deployment rollout exceeded its deadline"
    replicas = deployment["spec"]["replicas"]
    complete = all(status.get(key, 0) == replicas for key in
                   ("replicas", "updatedReplicas", "readyReplicas", "availableReplicas"))
    pod_uids = {pod["metadata"]["uid"] for pod in pods
                if any(container["image"] == image
                       for container in pod.get("spec", {}).get("containers", []))}
    endpoints = any(endpoint.get("conditions", {}).get("ready") is True
                    and endpoint.get("addresses")
                    and endpoint.get("targetRef", {}).get("uid") in pod_uids
                    for item in slices for endpoint in (item.get("endpoints") or []))
    if complete and endpoints:
        return True, False, "RolloutComplete", "All updated replicas and Service endpoints are ready"
    return False, False, "RolloutPending", "Waiting for updated replicas and ready Service endpoints"


def make_status(cr: Json, ready: bool, stalled: bool, reason: str,
                message: str, managed: bool) -> Json:
    generation = cr["metadata"]["generation"]
    previous = {item["type"]: item for item in cr.get("status", {}).get("conditions", [])}
    conditions = []
    for kind, value in (("Ready", ready), ("Stalled", stalled)):
        state = "True" if value else "False"
        old = previous.get(kind, {})
        transition = old.get("lastTransitionTime") if old.get("status") == state else None
        conditions.append({
            "type": kind, "status": state, "observedGeneration": generation,
            "reason": reason, "message": message,
            "lastTransitionTime": transition or datetime.now(timezone.utc).isoformat(
                timespec="seconds").replace("+00:00", "Z"),
        })
    name = cr["metadata"]["name"]
    return {
        "phase": "Ready" if ready else "Failed" if stalled else "Progressing",
        "observedGeneration": generation, "conditions": conditions,
        "managedResources": {"deployment": name, "service": name} if managed else {},
    }
