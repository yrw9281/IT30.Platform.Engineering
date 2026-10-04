import argparse
import json
import subprocess
import time


def current_condition(resource: dict, condition: str) -> bool:
    generation = resource["metadata"]["generation"]
    status = resource.get("status", {})
    return not resource["metadata"].get("deletionTimestamp") and status.get(
        "observedGeneration") == generation and any(
        item.get("type") == condition and item.get("status") == "True"
        and item.get("observedGeneration") == generation
        for item in status.get("conditions", []))


def wait_current(name: str, namespace: str, condition: str, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    generation = None
    uid = None
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["kubectl", "get", "microservice", name, "-n", namespace, "-o", "json"],
            stdout=subprocess.PIPE, text=True, check=True, timeout=30)
        resource = json.loads(result.stdout)
        current = resource["metadata"]["generation"]
        if generation is None:
            generation = current
            uid = resource["metadata"]["uid"]
        if current != generation or resource["metadata"]["uid"] != uid:
            raise RuntimeError("CR identity or spec changed while waiting; inspect the resource")
        if current_condition(resource, condition):
            print(f"{namespace}/{name}: generation={generation}, {condition}=True")
            return
        time.sleep(2)
    raise TimeoutError(
        f"{namespace}/{name}: {condition} not reached; last status={resource.get('status', {})}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("condition", choices=["Ready", "Stalled"])
    parser.add_argument("--name", default="todo-api")
    parser.add_argument("--namespace", default="todo")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    wait_current(args.name, args.namespace, args.condition, args.timeout)
