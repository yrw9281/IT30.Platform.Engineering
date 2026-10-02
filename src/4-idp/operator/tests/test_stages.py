from copy import deepcopy
import importlib.util
import logging
from pathlib import Path
import subprocess
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

import kopf
from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError
import yaml

import adopt
import resources
from validate_crs import invalid_inputs
from test_operator import cr

ROOT = Path(__file__).resolve().parents[1]


def load_stage(stage):
    spec = importlib.util.spec_from_file_location(f"stage_{stage}", ROOT / stage / "handlers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


day20 = load_stage("day20")
day21 = load_stage("day21")


class StageTests(unittest.TestCase):
    def setUp(self):
        self.cr = cr()
        self.logger = Mock(spec=logging.Logger)
        for key in ("api", "apps", "core", "custom"):
            item = patch.object(day21, key, Mock(), create=True)
            item.start()
            self.addCleanup(item.stop)
        day21.custom.get_namespaced_custom_object.return_value = self.cr

    def test_observer_only_accepts(self):
        status = {}
        day20.accept("todo-api", "todo", self.cr["spec"], self.logger,
                     Mock(status=status))
        self.assertEqual(status, {"phase": "Accepted"})

    def test_subset_resources_can_load_without_full_handlers(self):
        subset = ModuleType("resources")
        for key in ("Json", "InvalidSpec", "OwnershipConflict", "check_owner",
                    "contains", "desired_resources"):
            setattr(subset, key, getattr(resources, key))
        with patch.dict(sys.modules, {"resources": subset}):
            module = load_stage("day21")
        self.assertFalse(hasattr(module, "health"))
        self.assertFalse(hasattr(module, "discovery"))
        self.assertIs(module.desired_resources, resources.desired_resources)

    def test_success_creates_both_without_readiness(self):
        with patch.object(day21, "read_child", return_value=None):
            day21.reconcile("todo", "todo-api", self.logger)
        deployment, service = resources.desired_resources(self.cr)
        self.assertEqual(day21.apps.create_namespaced_deployment.call_args.args[1], deployment)
        self.assertEqual(day21.core.create_namespaced_service.call_args.args[1], service)
        status = day21.custom.patch_namespaced_custom_object_status.call_args.args[5]["status"]
        self.assertEqual(status["phase"], "ResourcesApplied")
        self.assertEqual(status["observedGeneration"], 2)
        self.assertEqual(status["conditions"], [])
        day21.core.list_namespaced_pod.assert_not_called()

    def test_service_update_preserves_ip_uid_and_resource_version(self):
        _, desired = resources.desired_resources(self.cr)
        current = deepcopy(desired)
        current["metadata"].update(uid="service-uid", resourceVersion="99")
        current["spec"].update(clusterIP="10.1.0.1", clusterIPs=["10.1.0.1"])
        current["spec"]["ports"][0]["port"] = 9090
        day21.ensure(desired, current, self.cr, self.logger)
        value = day21.core.replace_namespaced_service.call_args.args[2]
        self.assertEqual(value["metadata"]["uid"], "service-uid")
        self.assertEqual(value["metadata"]["resourceVersion"], "99")
        self.assertEqual(value["spec"]["clusterIP"], "10.1.0.1")
        self.assertEqual(value["spec"]["ports"][0]["port"], 8080)

    def test_identical_child_is_not_written(self):
        deployment, _ = resources.desired_resources(self.cr)
        day21.ensure(deployment, deepcopy(deployment), self.cr, self.logger)
        day21.apps.replace_namespaced_deployment.assert_not_called()

    def test_status_uses_latest_resource_version_and_clears_ready(self):
        latest = deepcopy(self.cr)
        latest["metadata"]["resourceVersion"] = "100"
        latest["status"] = {"phase": "Ready", "conditions": [{"type": "Ready", "status": "True"}]}
        day21.custom.get_namespaced_custom_object.return_value = latest
        day21.write_phase(self.cr, self.logger, "ResourcesApplied", True)
        body = day21.custom.patch_namespaced_custom_object_status.call_args.args[5]
        self.assertEqual(body["metadata"]["resourceVersion"], "100")
        self.assertEqual(body["status"]["conditions"], [])

    def test_stale_generation_uid_or_deletion_skips_status(self):
        for change in ({"generation": 3}, {"uid": "new"}, {"deletionTimestamp": "now"}):
            latest = deepcopy(self.cr)
            latest["metadata"].update(change)
            day21.custom.get_namespaced_custom_object.return_value = latest
            day21.write_phase(self.cr, self.logger, "ResourcesApplied", True)
            day21.custom.patch_namespaced_custom_object_status.assert_not_called()

    def test_invalid_spec_writes_failed_and_logs_cause(self):
        self.cr["spec"] = {}
        with self.assertRaises(kopf.PermanentError):
            day21.reconcile("todo", "todo-api", self.logger)
        self.logger.error.assert_called_once()
        status = day21.custom.patch_namespaced_custom_object_status.call_args.args[5]["status"]
        self.assertEqual(status["phase"], "Failed")
        self.assertEqual(status["conditions"], [])
        self.assertIsNone(status["managedResources"])
        day21.apps.create_namespaced_deployment.assert_not_called()

    def test_both_owners_are_preflighted_before_creating(self):
        _, service = resources.desired_resources(self.cr)
        service["metadata"]["ownerReferences"] = []
        with patch.object(day21, "read_child", side_effect=[None, service]):
            with self.assertRaises(kopf.PermanentError):
                day21.reconcile("todo", "todo-api", self.logger)
        day21.apps.create_namespaced_deployment.assert_not_called()
        day21.core.replace_namespaced_service.assert_not_called()

    def test_api_or_transport_errors_retry_even_when_reporting_failure(self):
        for error in (ApiException(status=409), HTTPError("connection lost")):
            with self.subTest(error=error):
                self.cr["spec"] = {}
                day21.custom.patch_namespaced_custom_object_status.side_effect = error
                with self.assertRaises(kopf.TemporaryError):
                    day21.reconcile("todo", "todo-api", self.logger)

    def test_deleted_cr_is_not_recreated(self):
        day21.custom.get_namespaced_custom_object.side_effect = ApiException(status=404)
        day21.reconcile("todo", "todo-api", self.logger)
        day21.apps.create_namespaced_deployment.assert_not_called()

    def test_timer_can_repair_missing_service(self):
        deployment, _ = resources.desired_resources(self.cr)
        with patch.object(day21, "read_child", side_effect=[deployment, None]):
            day21.reconcile("todo", "todo-api", self.logger)
        day21.apps.replace_namespaced_deployment.assert_not_called()
        day21.core.create_namespaced_service.assert_called_once()


class AdoptionTests(unittest.TestCase):
    def run_adoption(self, service_owner=None):
        resource = cr()
        deployment, service = resources.desired_resources(resource)
        deployment, service = deepcopy(deployment), deepcopy(service)
        for child in (deployment, service):
            child["metadata"].update(uid=f'{child["kind"]}-uid', resourceVersion="60")
            child["metadata"].pop("ownerReferences")
        service["spec"]["clusterIP"] = "10.1.0.1"
        if service_owner is not None:
            service["metadata"]["ownerReferences"] = [service_owner]
        api, apps, core, custom = Mock(), Mock(), Mock(), Mock()
        api.sanitize_for_serialization.side_effect = lambda item: item
        apps.read_namespaced_deployment.return_value = deployment
        core.read_namespaced_service.return_value = service
        custom.get_namespaced_custom_object.return_value = resource
        with patch.object(adopt.config, "load_kube_config"), \
                patch.object(adopt.client, "ApiClient", return_value=api), \
                patch.object(adopt.client, "AppsV1Api", return_value=apps), \
                patch.object(adopt.client, "CoreV1Api", return_value=core), \
                patch.object(adopt.client, "CustomObjectsApi", return_value=custom), \
                patch("builtins.print"):
            if service_owner is None:
                adopt.adopt()
            else:
                with self.assertRaises(resources.OwnershipConflict):
                    adopt.adopt()
        return apps, core

    def test_explicit_adoption_preserves_identity_and_ip(self):
        apps, core = self.run_adoption()
        deployment = apps.replace_namespaced_deployment.call_args.args[2]
        service = core.replace_namespaced_service.call_args.args[2]
        self.assertEqual(deployment["metadata"]["uid"], "Deployment-uid")
        self.assertEqual(service["spec"]["clusterIP"], "10.1.0.1")
        self.assertEqual(service["metadata"]["resourceVersion"], "60")
        resources.check_owner(deployment, cr())
        resources.check_owner(service, cr())

    def test_foreign_service_prevents_partial_adoption(self):
        apps, core = self.run_adoption({"uid": "foreign", "controller": True})
        apps.replace_namespaced_deployment.assert_not_called()
        core.replace_namespaced_service.assert_not_called()


class SourceContractTests(unittest.TestCase):
    def test_canonical_schema_and_examples(self):
        canonical = ROOT.parents[1] / "1-kubernetes" / "crd"
        schema = yaml.safe_load((canonical / "microservice-crd.yaml").read_text())[
            "spec"]["versions"][0]["schema"]["openAPIV3Schema"]
        self.assertEqual(schema["required"], ["spec"])
        self.assertEqual(set(schema["properties"]["spec"]["required"]), {"image", "port"})
        conditions = schema["properties"]["status"]["properties"]["conditions"]
        self.assertEqual(conditions["x-kubernetes-list-map-keys"], ["type"])
        resource = yaml.safe_load((canonical / "todo-api.yaml").read_text())
        self.assertEqual(resource["metadata"]["labels"]["app.kubernetes.io/owner"], "todo-team")
        self.assertEqual(resource["metadata"]["namespace"], "todo")
        self.assertEqual(invalid_inputs([resource]), [])
        invalid = yaml.safe_load((canonical / "invalid-todo-api.yaml").read_text())
        self.assertEqual(invalid_inputs([invalid]), ["todo/invalid-todo-api"])
        self.assertFalse((ROOT / "k8s" / "microservice-crd.yaml").exists())
        self.assertFalse((ROOT / "examples" / "todo-api.yaml").exists())
        self.assertFalse((ROOT / "day19" / "handlers.py").exists())

    def test_preflight_rejects_missing_spec_and_invalid_input_types(self):
        for spec in (None, {}, {"image": "", "port": 8080},
                     {"image": 3, "port": 8080}, {"image": "ok", "port": True},
                     {"image": "ok", "port": "8080"}, {"image": "ok", "port": 65536}):
            resource = cr()
            if spec is None:
                resource.pop("spec")
            else:
                resource["spec"] = spec
            with self.subTest(spec=spec):
                self.assertEqual(invalid_inputs([resource]), ["todo/todo-api"])


class DeploymentWiringTests(unittest.TestCase):
    def deploy(self, stage=None, missing=False, invalid=False):
        shell = """
kubectl() {
  printf '%s\\n' "MOCK kubectl $*" >&2
  case "$*" in
    'get crd microservices.platform.example.io')
      [ "$MISSING" != 1 ] || return 1 ;;
    'get microservices -A -o json')
      if [ "$INVALID" = 1 ]; then
        printf '%s\\n' '{"items":[{"metadata":{"namespace":"todo","name":"old"}}]}'
      else
        printf '%s\\n' '{"items":[]}'
      fi ;;
  esac
}
export -f kubectl
bash "$@"
"""
        arguments = [] if stage is None else [stage]
        return subprocess.run(
            ["bash", "-c", f"MISSING={int(missing)}; INVALID={int(invalid)}; "
             "export MISSING INVALID\n" + shell, "test-shell", str(ROOT / "deploy.sh"), *arguments],
            capture_output=True, text=True, check=False)

    def test_all_stages_select_expected_configmap_files(self):
        for stage, handler in (("day20", "day20/handlers.py"),
                               ("day21", "day21/handlers.py"), ("day22", "handlers.py")):
            with self.subTest(stage=stage):
                result = self.deploy(stage)
                self.assertEqual(result.returncode, 0, result.stderr)
                flag = f"--from-file=handlers.py={handler}" if stage != "day22" else "--from-file=handlers.py "
                self.assertIn(flag, result.stderr)
                self.assertEqual("--from-file=resources.py" in result.stderr, stage != "day20")
                self.assertEqual("get microservices -A" in result.stderr, stage == "day22")
                self.assertEqual("apply -f ../../1-kubernetes/crd/microservice-crd.yaml"
                                 in result.stderr, stage == "day22")
                self.assertNotIn("create namespace", result.stderr)

    def test_default_is_full_and_historical_stage_is_rejected(self):
        result = self.deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--from-file=resources.py", result.stderr)
        result = self.deploy("day19")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("renamed to day20", result.stderr)
        self.assertNotIn("MOCK kubectl", result.stderr)

    def test_missing_crd_explains_installation_without_deploying(self):
        result = self.deploy("day21", missing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("an administrator can install", result.stderr)
        self.assertIn("../../1-kubernetes/crd/microservice-crd.yaml", result.stderr)
        self.assertNotIn("MOCK kubectl create configmap", result.stderr)

    def test_incompatible_existing_cr_stops_before_crd_upgrade(self):
        result = self.deploy("day22", invalid=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("todo/old", result.stderr)
        self.assertNotIn("MOCK kubectl apply", result.stderr)
