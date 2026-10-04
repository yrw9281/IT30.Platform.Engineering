"""Exercise the deployed Operator in todo; restore the original CR spec on exit."""
import json
import subprocess
import time
from typing import Callable
import importlib.util
from pathlib import Path

spec_loader = importlib.util.spec_from_file_location(
    "wait_current", Path(__file__).resolve().parents[1] / "wait-current.py")
wait_current = importlib.util.module_from_spec(spec_loader)
spec_loader.loader.exec_module(wait_current)


def kubectl(*args: str, data: dict | None = None) -> str:
    result = subprocess.run(
        ["kubectl", *args], input=json.dumps(data) if data is not None else None,
        capture_output=True, text=True, check=True, timeout=90)
    return result.stdout


def get(kind: str, name: str) -> dict:
    return json.loads(kubectl("get", kind, name, "-n", "todo", "-o", "json"))


def wait(check: Callable[[], bool], description: str, timeout: int = 180) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            print("PASS:", description)
            return
        time.sleep(2)
    raise TimeoutError(description)


def ready() -> bool:
    resource = get("microservice", "todo-api")
    return wait_current.current_condition(resource, "Ready")


def set_spec(spec: dict) -> None:
    kubectl("patch", "microservice", "todo-api", "-n", "todo", "--type=merge",
            "-p", json.dumps({"spec": spec}))


def create_cr(name: str, spec: dict) -> None:
    kubectl("create", "-f", "-", data={
        "apiVersion": "platform.example.io/v1alpha1", "kind": "Microservice",
        "metadata": {"name": name, "namespace": "todo"}, "spec": spec})


def main() -> None:
    original = get("microservice", "todo-api")
    spec = original["spec"]
    deployment_uid = get("deployment", "todo-api")["metadata"]["uid"]
    service_uid = get("service", "todo-api")["metadata"]["uid"]
    for name in ("operator-repair-check", "operator-owner-check"):
        # Refuse to delete or overwrite a pre-existing test name.
        existing = json.loads(kubectl("get", "deployment,service,microservice",
                                      "-n", "todo", "--field-selector", f"metadata.name={name}",
                                      "-o", "json"))["items"]
        if existing:
            raise RuntimeError(f"Test name already exists: {name}")
    repair_created = owner_service_created = owner_cr_created = False
    try:
        wait(ready, "adopted workload is Ready at current generation")
        subprocess.run(["bash", str(Path(__file__).with_name("check_rollout.sh"))], check=True)
        assert get("deployment", "todo-api")["metadata"]["uid"] == deployment_uid
        assert get("service", "todo-api")["metadata"]["uid"] == service_uid
        wait(ready, "original image recovers")

        create_cr("operator-repair-check", spec)
        repair_created = True
        wait(lambda: bool(json.loads(kubectl(
            "get", "service", "operator-repair-check", "-n", "todo",
            "--ignore-not-found", "-o", "json") or "{}")), "test Service is created")
        first_uid = get("service", "operator-repair-check")["metadata"]["uid"]
        kubectl("delete", "service", "operator-repair-check", "-n", "todo")

        def repaired() -> bool:
            value = json.loads(kubectl("get", "service", "operator-repair-check",
                                      "-n", "todo", "--ignore-not-found", "-o", "json") or "{}")
            return bool(value) and value["metadata"]["uid"] != first_uid

        wait(repaired, "timer recreates deleted Service without changing CR spec")
        kubectl("delete", "microservice", "operator-repair-check", "-n", "todo", "--wait=true")
        repair_created = False
        wait(lambda: not json.loads(kubectl(
            "get", "deployment,service", "-n", "todo", "--field-selector",
            "metadata.name=operator-repair-check", "-o", "json"))["items"],
             "CR deletion garbage-collects its children and releases Kopf finalizer")

        kubectl("create", "service", "clusterip", "operator-owner-check",
                "-n", "todo", "--tcp=8080:8080")
        owner_service_created = True
        create_cr("operator-owner-check", spec)
        owner_cr_created = True
        wait(lambda: any(item.get("reason") == "OwnershipConflict"
                         for item in get("microservice", "operator-owner-check").get(
                             "status", {}).get("conditions", [])),
             "same-name foreign Service is rejected")
        assert not get("service", "operator-owner-check")["metadata"].get("ownerReferences")
        assert not kubectl("get", "deployment", "operator-owner-check", "-n", "todo",
                           "--ignore-not-found", "-o", "name").strip()
        kubectl("delete", "microservice", "operator-owner-check", "-n", "todo", "--wait=true")
        owner_cr_created = False
        kubectl("delete", "service", "operator-owner-check", "-n", "todo")
        owner_service_created = False

        kubectl("rollout", "restart", "deployment/microservice-operator", "-n", "todo")
        kubectl("rollout", "status", "deployment/microservice-operator", "-n", "todo", "--timeout=180s")
        wait(lambda: "[todo/todo-api] Resuming is processed: 1 succeeded; 0 failed." in kubectl(
            "logs", "deployment/microservice-operator", "-n", "todo", "-c", "operator")
             and ready(), "Operator restart resumes existing CR with fresh handler logs")
        print("PASS: original Deployment and Service UIDs are preserved")
    finally:
        set_spec(spec)
        if repair_created:
            kubectl("delete", "microservice", "operator-repair-check", "-n", "todo", "--wait=true")
        if owner_cr_created:
            kubectl("delete", "microservice", "operator-owner-check", "-n", "todo", "--wait=true")
        if owner_service_created:
            kubectl("delete", "service", "operator-owner-check", "-n", "todo")
        wait(ready, "original Todo API restored")


if __name__ == "__main__":
    main()
