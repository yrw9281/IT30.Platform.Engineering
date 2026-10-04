from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "wait_current", Path(__file__).resolve().parents[1] / "wait-current.py")
wait_current = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wait_current)


class WaitCurrentTests(unittest.TestCase):
    def setUp(self):
        self.resource = {
            "metadata": {"generation": 3, "uid": "original"},
            "status": {"observedGeneration": 3, "conditions": [
                {"type": "Ready", "status": "True", "observedGeneration": 3}]} }

    def test_requires_both_generation_markers(self):
        self.assertTrue(wait_current.current_condition(self.resource, "Ready"))
        for resource in (
                {**self.resource, "status": {**self.resource["status"], "observedGeneration": 2}},
                {**self.resource, "status": {"observedGeneration": 3, "conditions": [
                    {"type": "Ready", "status": "True", "observedGeneration": 2}]}}):
            self.assertFalse(wait_current.current_condition(resource, "Ready"))
        self.assertFalse(wait_current.current_condition(self.resource, "Stalled"))

    def test_spec_change_during_wait_is_explicit_failure(self):
        first = deepcopy(self.resource)
        first["status"] = {}
        second = deepcopy(first)
        second["metadata"]["generation"] = 4
        with patch.object(wait_current.subprocess, "run", side_effect=[
                Mock(stdout=json.dumps(first)), Mock(stdout=json.dumps(second))]), \
                patch.object(wait_current.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "spec changed"):
                wait_current.wait_current("todo-api", "todo", "Ready", 180)

    def test_same_generation_with_new_uid_is_not_the_same_request(self):
        first = deepcopy(self.resource)
        first["status"] = {}
        second = deepcopy(self.resource)
        second["metadata"]["uid"] = "recreated"
        with patch.object(wait_current.subprocess, "run", side_effect=[
                Mock(stdout=json.dumps(first)), Mock(stdout=json.dumps(second))]), \
                patch.object(wait_current.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "CR identity"):
                wait_current.wait_current("todo-api", "todo", "Ready", 180)

    def test_deleting_resource_is_not_ready(self):
        self.resource["metadata"]["deletionTimestamp"] = "2026-10-02T00:00:00Z"
        self.assertFalse(wait_current.current_condition(self.resource, "Ready"))

    def test_api_failure_is_not_treated_as_pending(self):
        with patch.object(wait_current.subprocess, "run",
                          side_effect=subprocess.CalledProcessError(1, "kubectl")):
            with self.assertRaises(subprocess.CalledProcessError):
                wait_current.wait_current("todo-api", "todo", "Ready", 180)
