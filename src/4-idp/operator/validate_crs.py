"""Preflight existing spec inputs before tightening the CRD; reads JSON on stdin."""
import json
import sys


def invalid_inputs(items: list[dict]) -> list[str]:
    invalid = []
    for resource in items:
        spec = resource.get("spec")
        if (not isinstance(spec, dict)
                or not isinstance(spec.get("image"), str) or len(spec["image"]) < 1
                or type(spec.get("port")) is not int or not 1 <= spec["port"] <= 65535):
            meta = resource["metadata"]
            invalid.append(f'{meta["namespace"]}/{meta["name"]}')
    return invalid


if __name__ == "__main__":
    invalid = invalid_inputs(json.load(sys.stdin)["items"])
    if invalid:
        sys.exit("Existing CRs incompatible with required spec/image/port; repair first: "
                 + ", ".join(invalid))
