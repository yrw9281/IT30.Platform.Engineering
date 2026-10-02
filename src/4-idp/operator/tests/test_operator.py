from copy import deepcopy
import logging
import unittest
from unittest.mock import Mock, patch

import kopf
from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError

import handlers
from resources import (
    LABEL, InvalidSpec, OwnershipConflict, check_owner, contains,
    desired_resources, health, make_status,
)


def cr():
    return {"apiVersion": "platform.example.io/v1alpha1", "kind": "Microservice",
            "metadata": {"name": "todo-api", "namespace": "todo", "uid": "cr-uid",
                         "generation": 2, "resourceVersion": "42"},
            "spec": {"image": "ghcr.io/yrw9281/it30-todo-api:0.1.0", "port": 8080}}


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.cr = cr()
        self.deployment, self.service = desired_resources(self.cr)
        self.deployment["metadata"]["generation"] = 5
        self.deployment["status"] = {
            "observedGeneration": 5, "replicas": 2, "updatedReplicas": 2,
            "availableReplicas": 2, "readyReplicas": 2,
        }
        self.pods = [{"metadata": {"uid": "pod-uid"},
                      "spec": {"containers": [{"name": "todo-api",
                                               "image": self.cr["spec"]["image"]}]}}]
        self.slices = [{"endpoints": [{"addresses": ["10.0.0.1"],
                                      "targetRef": {"uid": "pod-uid"},
                                      "conditions": {"ready": True}}]}]

    def test_resource_contract(self):
        selector = {"app": "todo-api"}
        self.assertEqual(self.deployment["spec"]["selector"]["matchLabels"], selector)
        self.assertEqual(self.service["spec"]["selector"], selector)
        self.assertEqual(self.service["spec"]["ports"][0]["targetPort"], "http")
        for item in (self.deployment, self.service):
            self.assertEqual(item["metadata"]["namespace"], "todo")
            check_owner(item, self.cr)
        container = self.deployment["spec"]["template"]["spec"]["containers"][0]
        self.assertEqual(container["ports"][0]["containerPort"], 8080)
        self.assertIn("resources", container)
        env = {item["name"]: item["value"] for item in container["env"]}
        self.assertEqual(env["OTEL_SERVICE_VERSION"], self.cr["spec"]["image"])

    def test_digest_and_port_are_preserved(self):
        self.cr["spec"] = {"image": "ghcr.io/yrw9281/it30-todo-api@sha256:" + "a" * 64,
                           "port": 9090}
        deployment, service = desired_resources(self.cr)
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        self.assertEqual(container["image"], self.cr["spec"]["image"])
        self.assertEqual(container["env"][0]["value"], "http://+:9090")
        self.assertEqual(service["spec"]["ports"][0]["port"], 9090)

    def test_invalid_inputs(self):
        for spec in ({}, {"image": "", "port": 8080},
                     {"image": "image", "port": True}, {"image": "image", "port": 65536}):
            with self.subTest(spec=spec), self.assertRaises(InvalidSpec):
                desired_resources({**self.cr, "spec": spec})
        self.cr["metadata"]["name"] = "a" * 64
        with self.assertRaises(InvalidSpec):
            desired_resources(self.cr)

    def test_does_not_adopt_same_name_or_non_controller_owner(self):
        for owner in ({}, {"uid": "other"}, {"uid": "cr-uid", "controller": False}):
            self.service["metadata"]["ownerReferences"] = [owner]
            with self.subTest(owner=owner), self.assertRaises(OwnershipConflict):
                check_owner(self.service, self.cr)

    def test_api_defaults_do_not_cause_updates(self):
        current = deepcopy(self.service)
        current["spec"]["clusterIP"] = "10.1.0.1"
        current["spec"]["ports"][0]["protocol"] = "TCP"
        self.assertTrue(contains(current, self.service))
        current["spec"]["ports"].append({"name": "unexpected", "port": 9999})
        self.assertFalse(contains(current, self.service))

    def test_rollout_and_endpoints_are_both_required(self):
        args = (self.deployment, self.slices, self.pods, self.cr["spec"]["image"])
        self.assertEqual(health(*args)[:3], (True, False, "RolloutComplete"))
        self.deployment["status"]["updatedReplicas"] = 1
        self.assertFalse(health(*args)[0])
        self.deployment["status"]["updatedReplicas"] = 2
        self.deployment["status"]["replicas"] = 3
        self.assertFalse(health(*args)[0])
        self.deployment["status"]["replicas"] = 2
        self.deployment["status"]["observedGeneration"] = 4
        self.assertEqual(health(*args)[2], "Reconciling")
        self.deployment["status"]["observedGeneration"] = 5
        self.slices[0]["endpoints"][0]["targetRef"]["uid"] = "unrelated"
        self.assertFalse(health(*args)[0])

    def test_image_pull_failure_and_recovery(self):
        self.pods[0]["status"] = {"containerStatuses": [{
            "name": "todo-api", "state": {"waiting": {"reason": "ImagePullBackOff"}}}]}
        self.assertEqual(health(self.deployment, self.slices, self.pods,
                                self.cr["spec"]["image"])[:3],
                         (False, True, "ImagePullBackOff"))
        self.pods[0].pop("status")
        self.assertTrue(health(self.deployment, self.slices, self.pods,
                               self.cr["spec"]["image"])[0])

    def test_empty_endpoint_slice_is_not_ready(self):
        self.assertFalse(health(self.deployment, [{"endpoints": None}], self.pods,
                                self.cr["spec"]["image"])[0])

    def test_transition_time_changes_only_with_condition_state(self):
        self.cr["status"] = make_status(self.cr, False, False, "Reconciling", "Applying", True)
        with patch("resources.datetime") as clock:
            clock.now.return_value.isoformat.return_value = "2099-01-01T00:00:00+00:00"
            status = make_status(self.cr, False, False, "RolloutPending", "Waiting", True)
            self.assertEqual(status["conditions"][0]["lastTransitionTime"],
                             self.cr["status"]["conditions"][0]["lastTransitionTime"])
            status = make_status(self.cr, True, False, "RolloutComplete", "Ready", True)
            self.assertEqual(status["conditions"][0]["lastTransitionTime"], "2099-01-01T00:00:00Z")
        self.assertEqual(status["observedGeneration"], 2)


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.cr = cr()
        self.logger = logging.getLogger("operator-test")
        self.patches = [patch.object(handlers, key, Mock(), create=True)
                        for key in ("api", "apps", "core", "custom", "discovery")]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_preserves_service_ip_and_resource_version(self):
        _, desired = desired_resources(self.cr)
        current = deepcopy(desired)
        current["metadata"]["resourceVersion"] = "50"
        current["spec"]["clusterIP"] = "10.1.0.1"
        current["spec"]["ports"][0]["port"] = 9090
        handlers.ensure(desired, current, self.cr, self.logger)
        replacement = handlers.core.replace_namespaced_service.call_args.args[2]
        self.assertEqual(replacement["spec"]["clusterIP"], "10.1.0.1")
        self.assertEqual(replacement["metadata"]["resourceVersion"], "50")
        self.assertEqual(replacement["spec"]["ports"][0]["port"], 8080)

    def test_identical_child_is_not_written(self):
        desired, _ = desired_resources(self.cr)
        handlers.ensure(desired, deepcopy(desired), self.cr, self.logger)
        handlers.apps.replace_namespaced_deployment.assert_not_called()

    def test_stale_generation_uid_and_deletion_skip_status(self):
        for change in ({"generation": 3}, {"uid": "recreated"}, {"deletionTimestamp": "now"}):
            latest = deepcopy(self.cr)
            latest["metadata"].update(change)
            handlers.custom.get_namespaced_custom_object.return_value = latest
            handlers.report(self.cr, self.logger, reason="RolloutPending", message="Waiting")
            handlers.custom.patch_namespaced_custom_object_status.assert_not_called()

    def test_status_patch_uses_fresh_resource_version(self):
        handlers.custom.get_namespaced_custom_object.return_value = self.cr
        handlers.report(self.cr, self.logger, reason="RolloutPending", message="Waiting")
        body = handlers.custom.patch_namespaced_custom_object_status.call_args.args[5]
        self.assertEqual(body["metadata"]["resourceVersion"], "42")

    def test_unmanaged_report_removes_previously_managed_names(self):
        self.cr["status"] = make_status(self.cr, True, False, "RolloutComplete", "Ready", True)
        handlers.custom.get_namespaced_custom_object.return_value = self.cr
        handlers.report(self.cr, self.logger, stalled=True, reason="OwnershipConflict",
                        message="Foreign Service")
        body = handlers.custom.patch_namespaced_custom_object_status.call_args.args[5]
        self.assertIsNone(body["status"]["managedResources"])
        self.assertEqual(body["status"]["phase"], "Failed")
        self.assertEqual(body["status"]["observedGeneration"], 2)

    def test_managed_report_retains_child_names(self):
        handlers.custom.get_namespaced_custom_object.return_value = self.cr
        handlers.report(self.cr, self.logger, ready=True, reason="RolloutComplete",
                        message="Ready", managed=True)
        body = handlers.custom.patch_namespaced_custom_object_status.call_args.args[5]
        self.assertEqual(body["status"]["managedResources"],
                         {"deployment": "todo-api", "service": "todo-api"})

    def test_failure_report_api_and_http_errors_retry(self):
        handlers.custom.get_namespaced_custom_object.return_value = self.cr
        for cause in (InvalidSpec("invalid image"), OwnershipConflict("foreign Service")):
            for error in (ApiException(status=409), HTTPError("connection lost")):
                with self.subTest(cause=cause, error=error), \
                        patch.object(handlers, "desired_resources", side_effect=cause), \
                        patch.object(handlers, "report", side_effect=error), \
                        patch.object(self.logger, "error") as log:
                    with self.assertRaises(kopf.TemporaryError) as raised:
                        handlers.reconcile("todo", "todo-api", self.logger)
                    self.assertIs(raised.exception.__cause__, error)
                    self.assertEqual(raised.exception.delay, 10)
                    self.assertEqual(log.call_count, 2)
        handlers.apps.create_namespaced_deployment.assert_not_called()

    def test_missing_cr_recheck_errors_are_logged_and_retried(self):
        for error in (ApiException(status=403), ApiException(status=503),
                      HTTPError("connection lost")):
            with self.subTest(error=error), patch.object(self.logger, "error") as log:
                handlers.custom.get_namespaced_custom_object.side_effect = [
                    ApiException(status=404), error]
                with self.assertRaises(kopf.TemporaryError) as raised:
                    handlers.reconcile("todo", "todo-api", self.logger)
                self.assertIs(raised.exception.__cause__, error)
                self.assertEqual(raised.exception.delay, 10)
                log.assert_called_once()
        handlers.apps.create_namespaced_deployment.assert_not_called()

    def test_api_conflicts_are_retried(self):
        handlers.custom.get_namespaced_custom_object.side_effect = ApiException(status=409)
        with self.assertRaises(kopf.TemporaryError):
            handlers.reconcile("todo", "todo-api", self.logger)

    def test_deleted_cr_is_not_recreated(self):
        handlers.custom.get_namespaced_custom_object.side_effect = ApiException(status=404)
        handlers.reconcile("todo", "todo-api", self.logger)
        handlers.apps.create_namespaced_deployment.assert_not_called()

    def test_service_ownership_conflict_does_not_create_deployment(self):
        handlers.custom.get_namespaced_custom_object.return_value = self.cr
        _, foreign = desired_resources(self.cr)
        foreign["metadata"]["ownerReferences"] = []
        with patch.object(handlers, "read_child", side_effect=[None, foreign]), \
                patch.object(handlers, "report") as report:
            with self.assertRaises(kopf.PermanentError):
                handlers.reconcile("todo", "todo-api", self.logger)
            report.assert_called_once()
        handlers.apps.create_namespaced_deployment.assert_not_called()


if __name__ == "__main__":
    unittest.main()
