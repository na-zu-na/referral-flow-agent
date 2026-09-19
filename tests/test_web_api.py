from __future__ import annotations

import time
import unittest

from web_api.app import create_app
from web_api.run_manager import RunManager


def _client():
    return create_app(manager=RunManager(confirmation_timeout=2)).test_client()


def _wait(client, job_id: str, wanted: set[str], timeout: float = 3):
    end = time.time() + timeout
    while time.time() < end:
        data = client.get(f"/api/runs/{job_id}").get_json()["data"]
        if data["status"] in wanted:
            return data
        time.sleep(0.01)
    raise AssertionError(f"run did not reach {wanted}: {data}")


class WebApiTests(unittest.TestCase):
    def test_case_and_evidence_endpoints(self):
        client = _client()
        self.assertEqual(client.get("/api/health").status_code, 200)
        response = client.get("/api/cases?tier=all&negative_case=true")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.get_json()["data"]["count"], 0)
        self.assertTrue(all(item["negative_case"] for item in response.get_json()["data"]["items"]))
        self.assertEqual(client.get("/api/cases/REF-5703").status_code, 200)
        self.assertEqual(client.get("/api/cases/UNKNOWN").status_code, 404)
        evidence = client.get("/api/evidence")
        self.assertEqual(evidence.status_code, 200)
        self.assertTrue(evidence.get_json()["data"]["d2"]["variants"])
        data = evidence.get_json()["data"]
        models = data["d5"]["models"]
        self.assertEqual(len(models), 6)
        self.assertFalse(any(item["model"].startswith("meta-llama/") for item in models))
        qwen = [item for item in models if item["model"].startswith("qwen/")]
        self.assertEqual({item["prompt_version"] for item in qwen}, {"v1", "v2"})
        claude = next(item for item in models if item["model"].startswith("anthropic/"))
        self.assertEqual(claude["scope"], "negative_only")
        self.assertIsNone(claude["final_pass_rate"])
        self.assertEqual(len(data["d6"]["pareto"]), 4)
        self.assertTrue(data["d6"]["cost_levers"])

    def test_negative_case_run_is_exposed_as_normal_guardrail_result(self):
        client = _client()
        created = client.post("/api/runs", json={"case_id": "REF-5703"})
        self.assertEqual(created.status_code, 202)
        job = _wait(client, created.get_json()["data"]["job_id"], {"guardrail_stopped", "completed", "failed"})
        self.assertEqual(job["status"], "guardrail_stopped")
        self.assertEqual(job["record"]["stopped_by"]["code"], "HOSTILE_INPUT_DETECTED")
        self.assertNotIn("transcript", job["record"])
        self.assertNotIn("moves", job["record"])
        self.assertNotIn("api_key", str(job))

    def test_booking_waits_for_web_confirmation(self):
        client = _client()
        created = client.post("/api/runs", json={"case_id": "REF-5602"}).get_json()["data"]
        waiting = _wait(client, created["job_id"], {"confirmation_required", "failed"})
        self.assertEqual(waiting["status"], "confirmation_required")
        self.assertEqual(waiting["confirmation"]["call"]["name"], "book_slot")
        response = client.post(f"/api/runs/{created['job_id']}/confirmation", json={"approved": True})
        self.assertEqual(response.status_code, 200)
        done = _wait(client, created["job_id"], {"completed", "failed"})
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["record"]["final"]["decision"], "book")

    def test_booking_can_be_rejected_without_booking(self):
        client = _client()
        created = client.post("/api/runs", json={"case_id": "REF-5602"}).get_json()["data"]
        _wait(client, created["job_id"], {"confirmation_required", "failed"})
        client.post(f"/api/runs/{created['job_id']}/confirmation", json={"approved": False})
        done = _wait(client, created["job_id"], {"confirmation_rejected", "failed"})
        self.assertEqual(done["status"], "confirmation_rejected")
        self.assertFalse(any(item["name"] == "book_slot" for item in done["record"]["observations"]))

    def test_audit_and_validation_endpoints(self):
        client = _client()
        runs = client.get("/api/audit/runs?negative_case=true&limit=2")
        self.assertEqual(runs.status_code, 200)
        items = runs.get_json()["data"]["items"]
        self.assertLessEqual(len(items), 2)
        self.assertTrue(all(item["negative_case"] for item in items))
        if items:
            calls = client.get(f"/api/audit/tool-calls?run_id={items[0]['run_id']}")
            self.assertEqual(calls.status_code, 200)
        self.assertEqual(client.get("/api/audit/runs?passed=maybe").status_code, 400)
        response = client.post("/api/runs", json={"case_id": "REF-5703", "temperature": -1})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
