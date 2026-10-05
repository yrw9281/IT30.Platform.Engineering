import ast
from copy import deepcopy
from pathlib import Path
import re
import subprocess
from textwrap import indent
import unittest

import yaml

from resources import make_status

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT.parents[2] / "doc" / "zh-tw"
CRD = ROOT.parents[1] / "1-kubernetes" / "crd"


def blocks(day: int, language: str) -> list[str]:
    text = (DOCS / f"D{day:02}.md").read_text()
    return re.findall(rf"^```{language}\n(.*?)^```$", text, re.M | re.S)


class ArticleSourceTests(unittest.TestCase):
    def test_observer_excerpt_matches_source(self):
        article = ast.parse(blocks(20, "python")[0]).body
        source = ast.parse((ROOT / "day20" / "handlers.py").read_text())
        accept = next(node for node in source.body
                      if isinstance(node, ast.FunctionDef) and node.name == "accept")
        self.assertEqual(len(article), 1)
        self.assertEqual(ast.dump(article[0], include_attributes=False),
                         ast.dump(accept, include_attributes=False))

    def test_deployment_excerpt_and_dependency_versions_match(self):
        deployment = yaml.safe_load((ROOT / "k8s" / "deployment.yaml").read_text())
        excerpt = yaml.safe_load(blocks(20, "yaml")[0])["spec"]
        self.assertEqual(excerpt, {
            key: deployment["spec"][key] for key in ("replicas", "strategy")})
        text = (DOCS / "D20.md").read_text()
        for requirement in (ROOT / "requirements.txt").read_text().splitlines():
            _, version = requirement.split("==")
            self.assertIn(f"`{version}`", text)
        pod = deployment["spec"]["template"]["spec"]
        self.assertEqual(pod["serviceAccountName"], "microservice-operator")
        self.assertEqual(deployment["metadata"]["namespace"], "todo")
        self.assertIn("--standalone", pod["containers"][0]["args"])
        self.assertIn("--namespace=todo", pod["containers"][0]["args"])

    def test_resource_management_excerpt_matches_stage21(self):
        self.assertEqual(len(blocks(21, "python")), 5)
        excerpt = blocks(21, "python")[0].strip()
        ast.parse(excerpt)
        self.assertIn(indent(excerpt, " " * 12),
                      (ROOT / "day21" / "handlers.py").read_text())

    def test_resource_helper_excerpts_match_complete_functions(self):
        examples = blocks(21, "python")
        for index, name, path in (
                (1, "read_child", ROOT / "day21" / "handlers.py"),
                (2, "check_owner", ROOT / "resources.py"),
                (3, "ensure", ROOT / "day21" / "handlers.py")):
            with self.subTest(function=name):
                article = ast.parse(examples[index]).body
                source = ast.parse(path.read_text())
                function = next(node for node in source.body
                                if isinstance(node, ast.FunctionDef) and node.name == name)
                self.assertEqual(len(article), 1)
                self.assertEqual(ast.dump(article[0], include_attributes=False),
                                 ast.dump(function, include_attributes=False))

    def test_resource_failure_excerpt_matches_exception_handler(self):
        article = ast.parse(blocks(21, "python")[4]).body
        source = ast.parse((ROOT / "day21" / "handlers.py").read_text())
        handler = next(node for node in ast.walk(source)
                       if isinstance(node, ast.ExceptHandler)
                       and isinstance(node.type, ast.Tuple)
                       and [item.id for item in node.type.elts] ==
                       ["InvalidSpec", "OwnershipConflict"])
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in article],
            [ast.dump(node, include_attributes=False) for node in handler.body])

    def test_replica_check_excerpt_matches_health(self):
        self.assertEqual(len(blocks(22, "python")), 1)
        excerpt = blocks(22, "python")[0].strip()
        ast.parse(excerpt)
        self.assertIn(indent(excerpt, " " * 4), (ROOT / "resources.py").read_text())

    def test_conditions_table_matches_status_builder(self):
        text = (DOCS / "D22.md").read_text()
        rows = re.findall(
            r'\| `(True|False)` \| `(True|False)` \| `(Progressing|Ready|Failed)` \|',
            text)
        resource = yaml.safe_load((CRD / "todo-api.yaml").read_text())
        resource["metadata"]["generation"] = 4
        expected = []
        for ready, stalled in ((False, False), (True, False), (False, True)):
            status = make_status(resource, ready, stalled, "Example", "Example", True)
            conditions = {item["type"]: item["status"] for item in status["conditions"]}
            expected.append((conditions["Ready"], conditions["Stalled"], status["phase"]))
        self.assertEqual(rows, expected)

    def test_stale_generation_example_matches_source_and_schema(self):
        example = yaml.safe_load(blocks(22, "yaml")[0])
        resource = yaml.safe_load((CRD / "todo-api.yaml").read_text())
        resource["metadata"]["generation"] = 3
        status = make_status(resource, True, False, "RolloutComplete", "Example", True)
        self.assertEqual(example["metadata"]["generation"], 4)
        for key in ("phase", "observedGeneration"):
            self.assertEqual(example["status"][key], status[key])
        ready = next(item for item in status["conditions"] if item["type"] == "Ready")
        shown = example["status"]["conditions"][0]
        self.assertEqual(shown, {key: ready[key] for key in shown})
        self.assertNotEqual(shown["observedGeneration"], example["metadata"]["generation"])
        current = deepcopy(resource)
        current["metadata"]["generation"] = 4
        self.assertEqual(make_status(
            current, True, False, "RolloutComplete", "Example", True)["observedGeneration"], 4)
        schema = yaml.safe_load((CRD / "microservice-crd.yaml").read_text())[
            "spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["status"]
        self.assertTrue(set(example["status"]) <= set(schema["properties"]))
        conditions = schema["properties"]["conditions"]
        self.assertEqual(conditions["x-kubernetes-list-map-keys"], ["type"])
        self.assertTrue(set(shown) <= set(conditions["items"]["properties"]))
        self.assertIn(shown["status"], conditions["items"]["properties"]["status"]["enum"])
        text = (DOCS / "D22.md").read_text()
        for key in conditions["items"]["required"]:
            self.assertIn(f"`{key}`", text)

    def test_rollout_commands_match_operational_readme(self):
        readme = (ROOT / "README.md").read_text().replace("\\\n", " ")
        normalized = " ".join(readme.split())
        for example in blocks(22, "bash"):
            for command in example.replace("\\\n", " ").splitlines():
                self.assertIn(" ".join(command.split()), normalized)

    def test_article_line_limits_and_no_repository_dependency(self):
        for day in range(20, 23):
            with self.subTest(day=day):
                text = (DOCS / f"D{day:02}.md").read_text()
                if day != 21:
                    self.assertLessEqual(len(text.splitlines()), 150)
                self.assertNotIn("<details>", text)
                self.assertNotRegex(text, r"src/|\brepo\b")
                self.assertNotRegex(
                    text, r"(?:完整實作|完整程式|原始碼).*(?:repository|儲存庫)")
                self.assertNotIn("github.com/yrw9281/IT30.Platform.Engineering", text)
                images = re.findall(r"!\[[^\]]+\]\((\.\./assets/[^)]+)\)", text)
                self.assertTrue("TODO(assets)" in text or images,
                                f"D{day:02} needs an asset placeholder or image")
                for image in images:
                    self.assertTrue((DOCS / image).is_file(),
                                    f"D{day:02} image does not exist: {image}")

    def test_shell_syntax_and_article_boundaries(self):
        subprocess.run(["bash", "-n", str(ROOT / "tests" / "check_rollout.sh")], check=True)
        for day in range(19, 23):
            text = (DOCS / f"D{day:02}.md").read_text()
            self.assertTrue(text.startswith(f"# Day {day:02} - "))
            inside = False
            headings = []
            for line in text.splitlines():
                if line.startswith("```"):
                    if not inside:
                        self.assertRegex(line, r"^```[a-z]+$")
                    else:
                        self.assertEqual(line, "```")
                    inside = not inside
                elif not inside and line.startswith("# "):
                    headings.append(line)
            self.assertEqual(len(headings), 1)
            self.assertFalse(inside, f"D{day:02} has an unclosed code block")
            self.assertNotIn("src/", text)
            self.assertNotRegex(text, r"(?m)^## (前言|驗收|結語)\s*$")
            self.assertNotRegex(text, r"(?:Day |D)(?:2[3-9]|30)\b")
            for example in blocks(day, "bash"):
                subprocess.run(["bash", "-n"], input=example, text=True, check=True)
