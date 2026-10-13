import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICIES = (
    "k8sdeploymentnoprivileged",
    "k8sdeploymentrequiredlimits",
    "k8smicroserviceimagepolicy",
)


def review(kind, spec, group="apps"):
    return {"review": {
        "kind": {"group": group, "kind": kind},
        "object": {"metadata": {"name": "todo-api"}, "spec": spec},
    }}


class PolicyTests(unittest.TestCase):
    def evaluate(self, policy, resource):
        template, _ = yaml.safe_load_all((ROOT / f"{policy}.yaml").read_text())
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory) / "policy.rego"
            module.write_text(template["spec"]["targets"][0]["rego"])
            result = subprocess.run(
                [os.environ.get("OPA", "opa"), "eval", "--v0-compatible",
                 "--format=json", "--data", str(module), "--stdin-input",
                 f"data.{policy}.violation"],
                input=json.dumps(resource), text=True, capture_output=True, check=True)
        return json.loads(result.stdout)["result"][0]["expressions"][0]["value"]

    def deployment(self, container, field="containers"):
        return review("Deployment", {"template": {"spec": {field: [container]}}})

    def test_privileged_for_regular_and_init_containers(self):
        for field in ("containers", "initContainers"):
            for context, expected in (({}, 0), ({"privileged": False}, 0),
                                      ({"privileged": True}, 1)):
                with self.subTest(field=field, context=context):
                    violations = self.evaluate(
                        POLICIES[0], self.deployment(
                            {"name": "todo-api", "securityContext": context}, field))
                    self.assertEqual(len(violations), expected)
                    if expected:
                        self.assertIn("todo-api", violations[0]["msg"])
                        self.assertIn("securityContext.privileged", violations[0]["msg"])

    def test_missing_and_empty_limits_for_regular_and_init_containers(self):
        cases = (
            (None, {"cpu", "memory"}),
            ({}, {"cpu", "memory"}),
            ({"limits": {}}, {"cpu", "memory"}),
            ({"limits": {"cpu": "500m"}}, {"memory"}),
            ({"limits": {"memory": "256Mi"}}, {"cpu"}),
            ({"limits": {"cpu": "500m", "memory": ""}}, {"memory"}),
            ({"limits": {"cpu": None, "memory": "256Mi"}}, {"cpu"}),
            ({"limits": {"cpu": "500m", "memory": "256Mi"}}, set()),
        )
        for field in ("containers", "initContainers"):
            for resources, missing in cases:
                with self.subTest(field=field, resources=resources):
                    container = {"name": "todo-api"}
                    if resources is not None:
                        container["resources"] = resources
                    violations = self.evaluate(
                        POLICIES[1], self.deployment(container, field))
                    self.assertEqual(
                        {item["msg"] for item in violations},
                        {f"container <todo-api> is missing resources.limits.{name}"
                         for name in missing})

    def test_all_containers_are_checked(self):
        spec = {"template": {"spec": {"containers": [
            {"name": "todo-api", "resources": {
                "limits": {"cpu": "500m", "memory": "256Mi"}}},
            {"name": "sidecar", "securityContext": {"privileged": True}},
        ]}}}
        for policy, count in ((POLICIES[0], 1), (POLICIES[1], 2)):
            with self.subTest(policy=policy):
                violations = self.evaluate(policy, review("Deployment", spec))
                self.assertEqual(len(violations), count)
                self.assertTrue(all("sidecar" in item["msg"] for item in violations))

    def test_image_repository_and_digest_format(self):
        prefix = "ghcr.io/yrw9281/it30-todo-api"
        valid = prefix + "@sha256:" + "a" * 64
        cases = (
            valid,
            prefix + ":0.1.0",
            prefix + "@sha256:" + "a" * 63,
            prefix + "@sha256:" + "a" * 65,
            prefix + "@sha256:" + "A" * 64,
            prefix + "@sha256:" + "g" * 64,
            valid + "\n",
            valid.replace("it30-todo-api", "it30-todo-api-other"),
            valid.replace("ghcr.io", "ghcrXio"),
            valid.replace("yrw9281", "other"),
            "",
            None,
        )
        for image in cases:
            with self.subTest(image=image):
                spec = {} if image is None else {"image": image}
                violations = self.evaluate(
                    POLICIES[2], review("Microservice", spec, "platform.example.io"))
                self.assertEqual(len(violations), 0 if image == valid else 1)
                if violations:
                    self.assertIn("todo-api", violations[0]["msg"])
                    self.assertIn("spec.image", violations[0]["msg"])

    def test_unhandled_kinds_and_groups_do_not_report_violations(self):
        for policy in POLICIES[:2]:
            self.assertEqual(self.evaluate(policy, review(
                "Pod", {"containers": [{"name": "todo-api",
                                        "securityContext": {"privileged": True}}]},
                "")), [])
        for kind, group in (("Deployment", "apps"), ("Microservice", "other.example.io")):
            self.assertEqual(self.evaluate(
                POLICIES[2], review(kind, {"image": "wrong"}, group)), [])

    def test_article_yaml_matches_sources_including_rego_comments(self):
        article = (ROOT.parents[2] / "doc/zh-tw/D29.md").read_text()
        excerpts = re.findall(r"^```yaml\n(.*?)^```$", article, re.M | re.S)
        sources = []
        for policy in POLICIES:
            sources.extend((ROOT / f"{policy}.yaml").read_text().split("---\n"))
        sources.append((ROOT / "todo-required-limits-exception.yaml").read_text())
        self.assertEqual(excerpts, sources)


if __name__ == "__main__":
    unittest.main()
