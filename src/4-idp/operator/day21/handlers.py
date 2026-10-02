import logging
from copy import deepcopy

import kopf
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError

from resources import (
    Json, InvalidSpec, OwnershipConflict, check_owner, contains, desired_resources,
)

GROUP, VERSION, PLURAL = "platform.example.io", "v1alpha1", "microservices"
TIMEOUT = (5, 20)
api: client.ApiClient
apps: client.AppsV1Api
core: client.CoreV1Api
custom: client.CustomObjectsApi


@kopf.on.startup()
def configure(settings, **_):
    global api, apps, core, custom
    config.load_incluster_config()
    api = client.ApiClient()
    apps = client.AppsV1Api(api)
    core = client.CoreV1Api(api)
    custom = client.CustomObjectsApi(api)
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage()
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage()
    settings.execution.max_workers = 1
    settings.posting.enabled = False
    settings.scanning.disabled = True


def read_cr(namespace: str, name: str) -> Json:
    return custom.get_namespaced_custom_object(
        GROUP, VERSION, namespace, PLURAL, name, _request_timeout=TIMEOUT)


def read_child(kind: str, namespace: str, name: str) -> Json | None:
    read = apps.read_namespaced_deployment if kind == "Deployment" else core.read_namespaced_service
    try:
        return api.sanitize_for_serialization(read(name, namespace, _request_timeout=TIMEOUT))
    except ApiException as error:
        if error.status == 404:
            return None
        raise


def ensure(desired: Json, current: Json | None, cr: Json, logger: logging.Logger) -> None:
    kind = desired["kind"]
    namespace, name = cr["metadata"]["namespace"], cr["metadata"]["name"]
    if current is None:
        create = (apps.create_namespaced_deployment if kind == "Deployment"
                  else core.create_namespaced_service)
        create(namespace, desired, _request_timeout=TIMEOUT)
        logger.info("Created %s/%s", kind, name)
        return
    check_owner(current, cr)
    if contains(current, desired):
        return
    replacement = deepcopy(current)
    replacement["metadata"]["labels"] = {
        **current["metadata"].get("labels", {}), **desired["metadata"]["labels"]}
    if kind == "Deployment":
        replacement["spec"] = desired["spec"]
        replace = apps.replace_namespaced_deployment
    else:
        replacement["spec"].update(desired["spec"])
        replace = core.replace_namespaced_service
    replacement.pop("status", None)
    replace(name, namespace, replacement, _request_timeout=TIMEOUT)
    logger.info("Updated %s/%s", kind, name)


def write_phase(cr: Json, logger: logging.Logger, phase: str, managed: bool) -> None:
    meta = cr["metadata"]
    latest = read_cr(meta["namespace"], meta["name"])
    if (latest["metadata"]["uid"] != meta["uid"]
            or latest["metadata"]["generation"] != meta["generation"]
            or latest["metadata"].get("deletionTimestamp")):
        logger.info("Skipping stale status for %s", meta["name"])
        return
    status = {
        "phase": phase, "observedGeneration": latest["metadata"]["generation"],
        "managedResources": {"deployment": meta["name"], "service": meta["name"]} if managed else {},
        "conditions": [],
    }
    if latest.get("status") != status:
        # Merge-patch null removes old resource names; [] removes stale Ready conditions.
        body = {**status, "managedResources": status["managedResources"] if managed else None}
        custom.patch_namespaced_custom_object_status(
            GROUP, VERSION, meta["namespace"], PLURAL, meta["name"],
            {"metadata": {"resourceVersion": latest["metadata"]["resourceVersion"]},
             "status": body}, _request_timeout=TIMEOUT)


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL, field="spec")
@kopf.on.resume(GROUP, VERSION, PLURAL)
@kopf.timer(GROUP, VERSION, PLURAL, interval=10)
def reconcile(namespace, name, logger, **_):
    try:
        cr = read_cr(namespace, name)
        if cr["metadata"].get("deletionTimestamp"):
            return
        try:
            desired_deployment, desired_service = desired_resources(cr)
            deployment = read_child("Deployment", namespace, name)
            service = read_child("Service", namespace, name)
            # Check both names before modifying either resource.
            for resource in (deployment, service):
                if resource is not None:
                    check_owner(resource, cr)
            ensure(desired_deployment, deployment, cr, logger)
            ensure(desired_service, service, cr, logger)
            write_phase(cr, logger, "ResourcesApplied", managed=True)
            logger.info("ResourcesApplied for %s/%s; readiness is not checked", namespace, name)
        except (InvalidSpec, OwnershipConflict) as error:
            logger.error("%s: %s", type(error).__name__, error)
            write_phase(cr, logger, "Failed", managed=False)
            raise kopf.PermanentError(str(error)) from error
    except ApiException as error:
        if error.status == 404:
            try:
                read_cr(namespace, name)
            except ApiException as missing:
                if missing.status == 404:
                    logger.info("CR %s/%s no longer exists", namespace, name)
                    return
                logger.error("Kubernetes API returned HTTP %s", missing.status)
                raise kopf.TemporaryError(
                    f"Kubernetes API returned HTTP {missing.status}", delay=10) from missing
            except HTTPError as missing:
                logger.error("Kubernetes API connection failed: %s", missing)
                raise kopf.TemporaryError("Kubernetes API connection failed", delay=10) from missing
        logger.error("Kubernetes API returned HTTP %s", error.status)
        raise kopf.TemporaryError(f"Kubernetes API returned HTTP {error.status}", delay=10) from error
    except HTTPError as error:
        logger.error("Kubernetes API connection failed: %s", error)
        raise kopf.TemporaryError("Kubernetes API connection failed", delay=10) from error
