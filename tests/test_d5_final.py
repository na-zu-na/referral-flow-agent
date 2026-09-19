"""Local, offline invariants for the final selected D5 5+1 package."""

import csv
import json
import sys
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

D5 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D5))

import final_5plus1 as final  # noqa: E402


class FinalFivePlusOneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = final.analyze(final.DEFAULT_CLAUDE)
        cls.rows = cls.result["rows"]

    def test_inventory_and_denominators(self):
        batteries = self.result["batteries"]
        self.assertEqual(len(batteries), 6)
        self.assertEqual(len({b["family"] for b in batteries[:5]}), 5)
        self.assertEqual([len(b["rows"]) for b in batteries], [52, 52, 52, 52, 18, 52])
        self.assertEqual(len(self.rows), 278)
        self.assertFalse(any("llama" in r["experiment_id"] for r in self.rows))
        self.assertEqual(
            [b["identity"]["operator"] for b in batteries],
            ["FAN YANXI", "HOU YUXUAN", "LIN SIYUAN", "WEN HAO", "CHEN CHANG", "ZHOU YU"],
        )

    def test_matched_negative_and_prompt_control_keys(self):
        batteries = self.result["batteries"]
        common_keys = {(f"REF-606{i}", trial) for i in range(6) for trial in (1, 2, 3)}
        for b in batteries[:5]:
            self.assertEqual({(r["case_id"], r["trial"]) for r in b["rows"]
                              if r["case_id"] in final.NEGATIVE_IDS}, common_keys)
        self.assertEqual({(r["case_id"], r["trial"]) for r in batteries[1]["rows"]},
                         {(r["case_id"], r["trial"]) for r in batteries[5]["rows"]})
        self.assertTrue(all(r["negative_case"] for r in batteries[4]["rows"]))

    def test_no_pass_label_change_and_incomplete_escalation_record(self):
        changes = [r for r in self.rows if r["changed"]]
        self.assertEqual(changes, [])
        corrected = next(r for r in self.rows if r["experiment_id"] == "mistral_small_3_2_v2"
                         and r["case_id"] == "REF-6062" and r["trial"] == 1)
        self.assertFalse(corrected["original_passed"])
        self.assertFalse(corrected["normalized_passed"])
        self.assertEqual(corrected["normalized_failure_reason"],
                         "available_slot_not_explicitly_declined")
        self.assertIn("no_unnecessary_slot_search", corrected["diagnostic_warnings"])
        self.assertTrue(all(not r["normalized_passed"] for r in self.rows
                            if r["status"] == "invalid_model_output"))
        self.assertEqual(Counter(r["experiment_id"] for r in self.rows),
                         Counter(dict(zip((s[0] for s in final.SELECTED),
                                          (52, 52, 52, 52, 18, 52)))))

    def test_reported_scores_and_provider_spend(self):
        self.assertEqual([s["normalized_passes"] for s in self.result["full"]],
                         [17, 28, 37, 39])
        self.assertEqual([s["normalized_passes"] for s in self.result["common"]],
                         [14, 6, 9, 12, 10])
        self.assertEqual([s["normalized_passes"] for s in self.result["qwen"]], [20, 28])
        claude = self.result["selected"][4]
        self.assertEqual((claude["original_passes"], claude["normalized_passes"],
                          claude["invalid_model_outputs"], claude["unsafe_booking_attempts"]),
                         (10, 10, 8, 0))
        self.assertEqual((claude["input_tokens"], claude["output_tokens"],
                          claude["cached_input_tokens"], claude["reasoning_tokens"]),
                         (272906, 11195, 0, 502))
        self.assertEqual(Decimal(claude["provider_spend_usd"]), Decimal("1.644405"))
        self.assertEqual(self.result["selected_spend_usd"], Decimal("2.13502002"))
        self.assertTrue(all(s["provider_cost_coverage"] == f"{s['runs']}/{s['runs']}"
                            for s in self.result["selected"]))

    def test_materialized_final_outputs(self):
        package = final.PACKAGE
        with (package / "SELECTED_5PLUS1_INVENTORY.csv").open(newline="", encoding="utf-8") as stream:
            inventory = list(csv.DictReader(stream))
        self.assertEqual(len(inventory), 6)
        self.assertEqual(sum(r["prompt_version"] == "v2" for r in inventory), 5)
        self.assertEqual(sum(r["prompt_version"] == "v1" for r in inventory), 1)
        self.assertEqual([r["team_price_tier"] for r in inventory],
                         ["lower_price"] * 4 + ["frontier", "lower_price"])
        index = json.loads((final.LIVE / "SELECTED_FINAL_INDEX.json").read_text(encoding="utf-8"))
        self.assertEqual(len(index["selected_v2"]), 5)
        self.assertEqual(len(index["prompt_control"]), 1)
        self.assertEqual(index["claude_overall_pass_rate"], "N/A_NEGATIVE_ONLY_SCOPE")
        self.assertEqual(index["changed_score_rows"], 0)
        self.assertFalse((final.LIVE / "llama3_3_70b_v2").exists())


if __name__ == "__main__":
    unittest.main()
