import json
import unittest
from pathlib import Path
from unittest.mock import patch

from agent import run_case
from backends.live import LiveBackend
from config import RunConfig


ROOT = Path(__file__).resolve().parents[1]


class SequenceBackend:
    name = "live"
    model = "test/fake-model"

    def __init__(self, moves, usage=None):
        self.moves = list(moves)
        self.usage = usage or {"input_tokens": 10, "output_tokens": 5, "measured": True}

    def next_move(self, transcript):
        del transcript
        move = self.moves.pop(0)
        return {
            "move": move,
            "usage": dict(self.usage),
        }


class Member1AgentTests(unittest.TestCase):
    def test_complete_booking_run_uses_four_logical_turns(self):
        record = run_case("REF-5602")

        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["final"]["decision"], "book")
        self.assertEqual(
            record["final"]["booked"],
            {"clinic": "OPH-C2", "date": "2026-10-14", "time": "11:20"},
        )
        self.assertEqual(record["turns"], 4)
        self.assertEqual(len(record["tool_calls"]), 5)
        self.assertEqual(record["tool_calls"][1]["turn"], record["tool_calls"][2]["turn"])
        self.assertIn("BOOKING_GATE_PASSED", {event["code"] for event in record["guardrail_events"]})
        self.assertTrue(record["run_id"])
        self.assertTrue(record["timestamp"].endswith("Z"))
        self.assertEqual(len(record["prompt_hash"]), 64)
        self.assertEqual(record["execution_mode"], "parallel")
        self.assertEqual(record["cost_source"], "locally_calculated")
        self.assertIsNone(record["provider_cost_usd"])
        for call in record["tool_calls"]:
            self.assertIsInstance(call["latency_ms"], float)
            self.assertIsInstance(call["observation_tokens"], int)
            self.assertIsInstance(call["observation_chars"], int)
            self.assertIsInstance(call["ok"], bool)

    def test_missing_test_finishes_without_slot_lookup(self):
        record = run_case("REF-5614")

        self.assertEqual(record["final"]["decision"], "request_information")
        self.assertEqual(record["final"]["missing"], "visual field test VF-01")
        self.assertNotIn("get_clinic_slots", [call["name"] for call in record["tool_calls"]])
        self.assertNotIn("book_slot", [call["name"] for call in record["tool_calls"]])

    def test_sequential_control_has_one_extra_turn_but_same_outcome(self):
        parallel = run_case("REF-5602", RunConfig(call_mode="parallel"))
        sequential = run_case("REF-5602", RunConfig(call_mode="sequential"))

        self.assertEqual(parallel["final"], sequential["final"])
        self.assertEqual(parallel["turns"], 4)
        self.assertEqual(sequential["turns"], 5)
        self.assertTrue(all(
            sum(call["turn"] == turn for call in sequential["tool_calls"]) == 1
            for turn in range(1, sequential["turns"] + 1)
        ))

    def test_selected_descriptor_version_shapes_real_slot_observation(self):
        v1 = run_case("REF-6064", RunConfig(descriptor_version="v1"))
        v2 = run_case("REF-6064", RunConfig(descriptor_version="v2"))

        def slot_data(record):
            return next(
                item["result"]["data"]
                for item in record["observations"]
                if item["name"] == "get_clinic_slots"
            )

        self.assertNotIn("requested_window", slot_data(v1))
        self.assertIn("requested_window", slot_data(v2))

    def test_hostile_text_causes_terminal_stop_and_no_later_call(self):
        record = run_case("REF-5703")

        self.assertEqual(record["status"], "guardrail_stopped")
        self.assertEqual(record["stopped_by"]["code"], "HOSTILE_INPUT_DETECTED")
        self.assertEqual(record["final"]["trigger"], "instruction_in_referral_free_text")
        self.assertEqual(
            [call["name"] for call in record["tool_calls"]],
            ["get_referral", "check_referral_criteria"],
        )

    def test_live_confirm_mode_never_auto_approves(self):
        script = json.loads(
            (ROOT / "backends/scripts/problem_b.json").read_text(encoding="utf-8")
        )["REF-5602"]
        config = RunConfig(backend="live", model="test/fake-model")
        record = run_case("REF-5602", config, backend=SequenceBackend(script))

        self.assertEqual(record["status"], "confirmation_required")
        self.assertIsNone(record["final"])
        self.assertFalse(any(item["name"] == "book_slot" for item in record["observations"]))

    def test_final_booking_without_booking_evidence_is_rejected(self):
        backend = SequenceBackend(
            [
                {
                    "type": "final",
                    "decision": "book",
                    "reason": "Unsupported claim.",
                    "booked": {
                        "clinic": "OPH-C2",
                        "date": "2026-10-14",
                        "time": "11:20",
                    },
                }
            ]
        )
        config = RunConfig(backend="live", model="test/fake-model")
        record = run_case("REF-5602", config, backend=backend)

        self.assertEqual(record["status"], "invalid_model_output")
        self.assertIn("not supported", record["error"]["message"])

    def test_provider_usage_details_and_cost_sources_are_preserved(self):
        script = json.loads(
            (ROOT / "backends/scripts/problem_b.json").read_text(encoding="utf-8")
        )["REF-5602"]
        usage = {
            "input_tokens": 10,
            "output_tokens": 5,
            "measured": True,
            "cached_input_tokens": 2,
            "reasoning_tokens": 1,
            "provider_cost_usd": 0.001,
        }
        config = RunConfig(
            backend="live",
            model="test/exact-model-id",
            autonomy="act",
            price_input_per_million=1.0,
            price_output_per_million=2.0,
        )
        record = run_case(
            "REF-5602",
            config,
            backend=SequenceBackend(script, usage=usage),
        )

        calls = len(script)
        self.assertEqual(record["model"], "test/fake-model")
        self.assertEqual(record["cached_input_tokens"], calls * 2)
        self.assertEqual(record["reasoning_tokens"], calls)
        self.assertEqual(record["provider_cost_usd"], calls * 0.001)
        self.assertGreater(record["calculated_cost_usd"], 0)
        self.assertEqual(record["cost_usd"], record["provider_cost_usd"])
        self.assertEqual(record["cost_source"], "provider_reported")

    def test_live_backend_extracts_optional_provider_usage_details(self):
        config = RunConfig(
            backend="live",
            model="provider/exact-model",
            api_key="test-key",
        )
        payload = {
            "choices": [{"message": {"content": json.dumps({
                "type": "final",
                "decision": "escalate",
                "reason": "Test response.",
                "trigger": "tool_failure",
            })}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "cost": 0.0123,
                "prompt_tokens_details": {"cached_tokens": 30},
                "completion_tokens_details": {"reasoning_tokens": 7},
            },
        }
        with patch("backends.live._post_openrouter", return_value=payload):
            response = LiveBackend(config, "system prompt").next_move([])

        self.assertEqual(response["usage"]["cached_input_tokens"], 30)
        self.assertEqual(response["usage"]["reasoning_tokens"], 7)
        self.assertEqual(response["usage"]["provider_cost_usd"], 0.0123)

    def test_invalid_live_output_still_records_provider_usage(self):
        config = RunConfig(backend="live", model="provider/exact-model", api_key="test-key")
        payload = {
            "choices": [{"message": {"content": "{} trailing"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.0123},
        }
        with patch("backends.live._post_openrouter", return_value=payload):
            record = run_case("REF-5602", config)

        self.assertEqual(record["status"], "invalid_model_output")
        self.assertTrue(record["tokens_measured"])
        self.assertEqual(record["tokens_in"], 100)
        self.assertEqual(record["tokens_out"], 20)
        self.assertEqual(record["provider_cost_usd"], 0.0123)

    def test_all_authored_scripts_match_the_supplied_code_check_fields(self):
        expected = json.loads(
            (ROOT / "data/expected_outcomes_B.json").read_text(encoding="utf-8")
        )
        for target in expected:
            with self.subTest(case_id=target["case_id"]):
                record = run_case(target["case_id"])
                final = record["final"]
                self.assertEqual(final["decision"], target["expected_decision"])
                if final["decision"] == "book":
                    self.assertEqual(final["booked"], target["booked"])
                elif final["decision"] == "request_information":
                    self.assertEqual(final["missing"], target["missing"])
                else:
                    self.assertEqual(final["trigger"], target["trigger"])


if __name__ == "__main__":
    unittest.main()
