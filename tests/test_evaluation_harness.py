import csv
import copy
import json
import tempfile
import unittest
from pathlib import Path

from evaluation.harness import (
    DATA,
    RUN_LOG_FIELDS,
    TOOL_CALL_LOG_FIELDS,
    evaluate,
    load_reviews,
    rescore_saved,
    score_record,
    select_cases,
    summarize,
    write_results,
)


class EvaluationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.case = next(x for x in select_cases(data_dir=DATA, tier="core") if x["case_id"] == "REF-6060")
        self.answer = {
            "case_id": "REF-6060", "expected_decision": "escalate",
            "trigger": "red_flag_term", "must_record": ["red flag identified"],
        }
        self.record = {
            "case_id": "REF-6060", "status": "completed", "autonomy": "confirm",
            "prompt_version": "v2", "descriptor_version": "v2", "call_mode": "parallel",
            "final": {"decision": "escalate", "trigger": "red_flag_term"},
            "tool_calls": [
                {"id": "r1", "name": "get_referral"},
                {"id": "r2", "name": "check_referral_criteria"},
            ],
            "moves": [
                {"type": "tool_calls", "calls": [{"id": "r1", "name": "get_referral"}]},
                {"type": "tool_calls", "calls": [{"id": "r2", "name": "check_referral_criteria"}]},
                {"type": "final", "decision": "escalate", "trigger": "red_flag_term"},
            ],
            "observations": [
                {"name": "get_referral", "result": {"ok": True, "data": {
                    "referral_id": "REF-6060", "specialty": "CARD",
                }}},
                {"name": "check_referral_criteria", "result": {"ok": True, "data": {
                    "red_flags_detected": ["sudden visual loss"],
                    "window_start": "2026-09-09", "window_end": "2026-09-23",
                }}},
            ],
            "guardrail_events": [], "stopped_by": None,
        }

    def test_correct_structured_run_stays_pending_until_prose_review(self):
        result = score_record(self.case, self.answer, self.record, 1)
        self.assertTrue(result["automatic_pass"])
        self.assertIsNone(result["passed"])
        self.assertEqual(result["review_status"], "pending")

    def test_correct_decision_for_wrong_reason_fails(self):
        self.record["final"]["trigger"] = "specialty_mismatch"
        result = score_record(self.case, self.answer, self.record, 1)
        self.assertFalse(result["automatic_pass"])
        self.assertIn("trigger", result["failures"])
        self.assertFalse(result["passed"])

    def test_blocked_booking_attempt_on_negative_case_is_still_a_failure(self):
        self.record["moves"].append({"type": "tool_calls", "calls": [{"id": "r3", "name": "book_slot"}]})
        result = score_record(self.case, self.answer, self.record, 1)
        self.assertIn("no_booking_attempt", result["failures"])
        self.assertIn("no_successful_booking", result["checks"])

    def test_term_present_only_in_answer_is_not_observed_evidence(self):
        self.record["observations"][1]["result"]["data"]["red_flags_detected"] = []
        result = score_record(self.case, self.answer, self.record, 1)
        self.assertIn("trigger_supported_by_observation", result["failures"])

    def test_harmless_extra_lookup_is_diagnostic_not_outcome_failure(self):
        record = copy.deepcopy(self.record)
        query = {"id": "r3", "name": "get_clinic_slots", "arguments": {}}
        record["moves"].insert(-1, {"type": "tool_calls", "calls": [query]})
        record["observations"].append({
            "name": "get_clinic_slots",
            "result": {"ok": True, "data": {"slots": []}},
        })
        result = score_record(self.case, self.answer, record, 1, review_verdict=True)
        self.assertTrue(result["automatic_pass"])
        self.assertTrue(result["passed"])
        self.assertFalse(result["diagnostic_clean"])
        self.assertIn("no_unnecessary_slot_search", result["diagnostic_warnings"])
        self.assertNotIn("no_unnecessary_slot_search", result["outcome_failures"])

    def test_claim_level_reviews_require_all_claims_to_be_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["case_id", "trial", "claim", "verdict", "reviewer"])
                writer.writerow(["REF-6060", 1, "first", "accept", "Reviewer A"])
                writer.writerow(["REF-6060", 1, "second", "", ""])
                writer.writerow(["REF-6060", 2, "first", "accept", "Reviewer A"])
                writer.writerow(["REF-6060", 2, "second", "accept", "Reviewer A"])
                writer.writerow(["REF-6060", 3, "first", "reject", "Reviewer B"])
            reviews = load_reviews(path)
        self.assertTrue(reviews[("REF-6060", 1)]["first"]["accepted"])
        self.assertEqual(
            reviews[("REF-6060", 2)]["second"]["reviewer"], "Reviewer A"
        )
        self.assertFalse(reviews[("REF-6060", 3)]["first"]["accepted"])
        self.assertIsNone(score_record(
            self.case, self.answer, self.record, 1,
            review_verdict={"different claim": True},
        )["passed"])
        named = score_record(
            self.case, self.answer, self.record, 1,
            review_verdict={
                "red flag identified": {
                    "accepted": True,
                    "reviewer": "Reviewer A",
                    "reviewed_at": "2026-09-17",
                }
            },
        )
        self.assertTrue(named["passed"])
        self.assertEqual(named["reviewers"], ["Reviewer A"])

    def test_completed_review_requires_named_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.csv"
            path.write_text(
                "case_id,trial,claim,verdict,reviewer\n"
                "REF-6060,1,red flag identified,accept,\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "reviewer is required"):
                load_reviews(path)

    def test_evaluate_runs_three_independent_trials(self):
        called = []

        def runner(case_id):
            called.append(case_id)
            return self.record.copy()

        results = evaluate(runner, data_dir=DATA, tier="core", case_ids={"REF-6060"})
        self.assertEqual(called, ["REF-6060"] * 3)
        self.assertEqual([item["trial"] for item in results], [1, 2, 3])

    def test_rescore_uses_saved_record_and_complete_claim_verdicts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trials.jsonl"
            path.write_text(json.dumps({
                "case_id": "REF-6060", "trial": 1, "record": self.record,
            }) + "\n", encoding="utf-8")
            original_claims = next(
                item["must_record"] for item in json.loads(
                    (DATA / "expected_outcomes_B.json").read_text(encoding="utf-8")
                ) if item["case_id"] == "REF-6060"
            )
            incomplete = rescore_saved(path, reviews={
                ("REF-6060", 1): {original_claims[0]: True},
            })
            accepted = rescore_saved(path, reviews={
                ("REF-6060", 1): {claim: True for claim in original_claims},
            })
        self.assertIsNone(incomplete[0]["passed"])
        self.assertTrue(accepted[0]["passed"])

    def test_negative_final_rate_waits_for_negative_claim_review(self):
        base = {
            "automatic_pass": True, "failures": [], "expected_decision": "escalate",
            "status": "completed", "backend": "scripted", "model": None,
            "tokens_measured": False, "turns": 2, "cost_usd": 0,
            "policy": "prompt_version=v2|descriptor_version=v2|call_mode=parallel|autonomy=confirm",
        }
        results = [
            {**base, "case_id": "N1", "negative_case": True, "passed": True},
            {**base, "case_id": "N2", "negative_case": True, "passed": None},
            {**base, "case_id": "P1", "negative_case": False, "passed": True},
        ]
        pending = summarize(results)
        self.assertEqual(pending["negative_final_pass"], 1)
        self.assertEqual(pending["negative_pending_review"], 1)
        self.assertIsNone(pending["negative_final_pass_rate"])
        results[1]["passed"] = False
        results[1]["automatic_pass"] = False
        results[1]["failures"] = ["decision"]
        settled = summarize(results)
        self.assertEqual(settled["negative_pending_review"], 0)
        self.assertEqual(settled["negative_final_pass_rate"], 0.5)
        self.assertEqual(settled["automatic_failure_categories"], {"decision": 1})
        self.assertEqual(settled["outcome_pass_rate"], 2 / 3)
        self.assertEqual(settled["diagnostic_clean_rate"], 1.0)
        self.assertEqual(settled["final_failures"], 1)
        self.assertEqual(settled["median_turns"], 2)
        self.assertEqual(settled["worst_turns"], 2)
        self.assertEqual(settled["trials_per_case"], 1)
        self.assertEqual(len(settled["by_policy_model"]), 1)
        self.assertEqual(settled["by_policy_model"][0]["final_pass_rate"], 2 / 3)

    def test_negative_pending_total_spans_policy_model_groups(self):
        base = {
            "automatic_pass": True, "failures": [], "diagnostic_clean": True,
            "diagnostic_warnings": [], "expected_decision": "escalate",
            "status": "completed", "backend": "scripted", "model": None,
            "tokens_measured": False, "turns": 2, "cost_usd": 0,
            "negative_case": True, "passed": None,
        }
        results = [
            {**base, "case_id": "N1", "policy": "policy-a"},
            {**base, "case_id": "N2", "policy": "policy-b"},
        ]
        summary = summarize(results)
        self.assertEqual(summary["negative_pending_review"], 2)
        self.assertEqual(len(summary["by_policy_model"]), 2)

    def test_no_slot_escalation_requires_query_in_assessed_band(self):
        case = next(x for x in select_cases(data_dir=DATA, tier="core") if x["case_id"] == "REF-6064")
        answer = {"case_id": "REF-6064", "expected_decision": "escalate",
                  "trigger": "no_slot_in_window", "must_record": []}
        record = copy.deepcopy(self.record)
        record["case_id"] = "REF-6064"
        record["final"] = {"decision": "escalate", "trigger": "no_slot_in_window"}
        record["observations"][0]["result"]["data"].update(referral_id="REF-6064", specialty="DER")
        record["observations"][1]["result"]["data"].update(
            red_flags_detected=[], band="urgent", window_start="2026-09-09", window_end="2026-09-23"
        )
        query = {"id": "r3", "name": "get_clinic_slots", "arguments": {
            "specialty": "DER", "band": "urgent", "window_start": "2026-09-09", "window_end": "2026-09-23",
        }}
        record["tool_calls"].append(query)
        record["moves"].insert(-1, {"type": "tool_calls", "calls": [query]})
        record["observations"].append({"name": "get_clinic_slots", "result": {"ok": True, "data": {
            "result": "NO_SLOT_WITHIN_WINDOW", "slots": [],
            "requested_window": {"start": "2026-09-09", "end": "2026-09-23"},
        }}})
        self.assertTrue(score_record(case, answer, record, 1)["automatic_pass"])
        record["descriptor_version"] = "v1"
        del record["observations"][-1]["result"]["data"]["requested_window"]
        self.assertTrue(score_record(case, answer, record, 1)["automatic_pass"])
        query["arguments"]["band"] = "soon"
        wrong_band = score_record(case, answer, record, 1)
        self.assertIn("slot_search_exact_assessed_band", wrong_band["failures"])

    def test_write_results_exports_canonical_run_and_tool_call_logs(self):
        record = copy.deepcopy(self.record)
        record.update({
            "run_id": "run-1",
            "timestamp": "2026-09-17T00:00:00Z",
            "model": "test/exact-model",
            "prompt_version": "v2",
            "prompt_hash": "a" * 64,
            "descriptor_version": "v2",
            "backend": "live",
            "execution_mode": "parallel",
            "temperature": 0.0,
            "tokens_in": 12,
            "tokens_out": 3,
            "tokens_measured": True,
            "cached_input_tokens": 2,
            "reasoning_tokens": 1,
            "provider_cost_usd": 0.01,
            "calculated_cost_usd": 0.02,
            "cost_source": "provider_reported",
            "cost_usd": 0.01,
            "latency_ms": 4.5,
            "error": None,
        })
        for turn, call in enumerate(record["tool_calls"], 1):
            call.update({
                "turn": turn,
                "observation_tokens": 10,
                "observation_chars": 40,
                "latency_ms": 1.25,
                "ok": True,
                "error_code": None,
            })
        result = score_record(self.case, self.answer, record, 1, review_verdict=True)

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            write_results([result], out)
            with (out / "runs.csv").open(newline="", encoding="utf-8") as stream:
                run_reader = csv.DictReader(stream)
                run_rows = list(run_reader)
                self.assertEqual(run_reader.fieldnames, RUN_LOG_FIELDS)
            with (out / "tool_calls.csv").open(newline="", encoding="utf-8") as stream:
                tool_reader = csv.DictReader(stream)
                tool_rows = list(tool_reader)
                self.assertEqual(tool_reader.fieldnames, TOOL_CALL_LOG_FIELDS)

        self.assertEqual(run_rows[0]["run_id"], "run-1")
        self.assertEqual(run_rows[0]["decision"], "escalate")
        self.assertEqual(run_rows[0]["provider_cost_usd"], "0.01")
        self.assertEqual(len(tool_rows), 2)
        self.assertEqual(tool_rows[0]["tool_name"], "get_referral")
        self.assertEqual(tool_rows[0]["observation_tokens"], "10")


if __name__ == "__main__":
    unittest.main()
