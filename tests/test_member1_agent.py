import json
import unittest
from pathlib import Path

from agent import run_case
from config import RunConfig


ROOT = Path(__file__).resolve().parents[1]


class SequenceBackend:
    name = "live"
    model = "test/fake-model"

    def __init__(self, moves):
        self.moves = list(moves)

    def next_move(self, transcript):
        del transcript
        move = self.moves.pop(0)
        return {
            "move": move,
            "usage": {"input_tokens": 10, "output_tokens": 5, "measured": True},
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
