"""Exercise event-only and resource-only stages; leave the full Operator running."""
from pathlib import Path
import subprocess

from check_cluster import create_cr, get, kubectl, wait

ROOT = Path(__file__).resolve().parents[1]
EVENT = "operator-event-check"
REPAIR = "operator-repair-check"
OWNER = "operator-owner-check"


def deploy(stage: str) -> None:
    subprocess.run(["bash", str(ROOT / "deploy.sh"), stage], check=True)


def named_resources(name: str) -> str:
    return kubectl("get", "deployment,service,microservice", "-n", "todo",
                   "--field-selector", f"metadata.name={name}", "-o", "name").strip()


def logs() -> str:
    return kubectl("logs", "deployment/microservice-operator", "-n", "todo", "-c", "operator")


def main() -> None:
    spec = get("microservice", "todo-api")["spec"]
    for name in (EVENT, REPAIR, OWNER):
        if named_resources(name):
            raise RuntimeError(f"Test name already exists: {name}")
    created = set()
    foreign_service = False
    try:
        deploy("day20")
        create_cr(EVENT, spec)
        created.add(EVENT)
        wait(lambda: get("microservice", EVENT).get("status", {}).get("phase") == "Accepted",
             "create event writes Accepted")
        assert kubectl("get", "deployment,service", "-n", "todo", "--field-selector",
                       f"metadata.name={EVENT}", "-o", "name").strip() == ""
        kubectl("patch", "microservice", EVENT, "-n", "todo", "--type=merge",
                "-p", '{"spec":{"port":9090}}')
        wait(lambda: f"Accepted todo/{EVENT}:" in logs()
             and "port=9090" in logs(), "spec update reaches observer")
        deploy("day20")
        wait(lambda: f"[todo/{EVENT}] Resuming is processed: 1 succeeded; 0 failed." in logs(),
             "new observer Pod resumes existing CR")
        kubectl("delete", "microservice", EVENT, "-n", "todo", "--wait=true")
        created.remove(EVENT)

        deploy("day21")
        create_cr(REPAIR, spec)
        created.add(REPAIR)
        wait(lambda: get("microservice", REPAIR).get("status", {}).get(
            "phase") == "ResourcesApplied", "resource-only stage submits both children")
        first_uid = get("service", REPAIR)["metadata"]["uid"]
        kubectl("delete", "service", REPAIR, "-n", "todo")
        wait(lambda: bool(kubectl("get", "service", REPAIR, "-n", "todo",
                                  "--ignore-not-found", "-o", "name").strip()),
             "resource-only timer repairs deleted Service")
        assert get("service", REPAIR)["metadata"]["uid"] != first_uid
        kubectl("delete", "microservice", REPAIR, "-n", "todo", "--wait=true")
        created.remove(REPAIR)
        wait(lambda: not named_resources(REPAIR), "resource-only children are garbage-collected")

        kubectl("create", "service", "clusterip", OWNER, "-n", "todo", "--tcp=8080:8080")
        foreign_service = True
        create_cr(OWNER, spec)
        created.add(OWNER)
        wait(lambda: get("microservice", OWNER).get("status", {}).get("phase") == "Failed"
             and "OwnershipConflict" in logs(), "resource-only stage reports ownership conflict")
        assert not get("service", OWNER)["metadata"].get("ownerReferences")
        assert not kubectl("get", "deployment", OWNER, "-n", "todo",
                           "--ignore-not-found", "-o", "name").strip()
    finally:
        try:
            for name in created:
                kubectl("delete", "microservice", name, "-n", "todo", "--wait=true")
            if foreign_service:
                kubectl("delete", "service", OWNER, "-n", "todo")
        finally:
            deploy("day22")
            subprocess.run(["python3", str(ROOT / "wait-current.py"), "Ready"], check=True)


if __name__ == "__main__":
    main()
