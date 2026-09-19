"""Offline regression checks for the frozen final D5 5+1 selection."""
import csv
import json
import unittest
from decimal import Decimal
from pathlib import Path

import numpy as np

from D6_cost_analysis.src.bootstrap import bootstrap_metrics, cluster_sample
from D6_cost_analysis.src.config import D6, FAILURE_COST_USD, MONTHLY_REFERRALS
from D6_cost_analysis.src.cost_engine import break_even, case_balanced_mean, pass_rates, sensitivity_rates
from D6_cost_analysis.src.loaders import inventory, load_batteries, score_rows
from D6_cost_analysis.src.normalization import normalized_runs, normalized_tool_calls
from D6_cost_analysis.src.pareto import pareto_status
from D6_cost_analysis.src.pipeline import _common_negative, _safety, _spend, _summaries
from D6_cost_analysis.src.failure_analysis import taxonomy_rows


def output_rows(name):
    with (D6/"outputs"/name).open(encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


class FrozenSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batteries=load_batteries()
        cls.runs=normalized_runs(cls.batteries)
        for run in cls.runs:
            run["recomputed_ai_cost_usd"]=None
        cls.taxonomy=taxonomy_rows(cls.runs,cls.batteries)
        cls.safety,lookup=_safety(cls.runs,cls.batteries)
        cls.summary=_summaries(cls.runs,cls.taxonomy,lookup)
        cls.common=_common_negative(cls.runs,cls.taxonomy)

    def test_selected_structure_and_source_audit(self):
        self.assertEqual(len(inventory()),6)
        self.assertEqual(len(self.runs),278)
        self.assertEqual(len(score_rows()),278)
        self.assertEqual(sum(x["scope"]=="full_battery" and x["prompt_version"]=="v2" for x in inventory()),4)
        self.assertEqual({x["scope"] for x in inventory()},{"full_battery","negative_only","prompt_control"})
        self.assertEqual(sum(r["provider_cost_usd"] is not None for r in self.runs),278)
        self.assertEqual({r["backend"] for r in self.runs},{"live"})
        self.assertEqual(sum(r["status"]=="invalid_model_output" for r in self.runs),89)
        self.assertTrue(all(not r["passed"] for r in self.runs if r["status"]=="invalid_model_output"))

    def test_full_battery_pass_invalid_and_case_balanced(self):
        expected={
            "openai_gpt4o_mini_v2":(17,35,29644.075883888887),
            "qwen3_30b_v2":(28,14,14672.840641666666),
            "mistral_small_3_2_v2":(37,0,8258.426726666665),
            "gemini2_5_flash_v2":(39,6,8266.09277),
        }
        for bid,(passed,invalid,monthly) in expected.items():
            group=[r for r in self.runs if r["experiment_id"]==bid]
            self.assertEqual((len(group),sum(r["passed"] for r in group)),(52,passed))
            self.assertEqual(sum(r["status"]=="invalid_model_output" for r in group),invalid)
            ai,observed,total=case_balanced_mean(group,"provider_cost_usd")
            self.assertEqual((observed,total),(40,40))
            case_pass=pass_rates(group)[1]
            self.assertAlmostEqual(MONTHLY_REFERRALS*(ai+(1-case_pass)*float(FAILURE_COST_USD)),monthly,places=6)

    def test_claude_negative_only_and_no_general_cost(self):
        s=next(x for x in self.summary if x["scope"]=="FRONTIER_NEGATIVE_ONLY")
        self.assertEqual((s["runs"],s["unique_cases"],s["passed_runs"],s["invalid_model_output_count"]),(18,6,10,8))
        self.assertEqual((s["total_input_tokens"],s["total_output_tokens"],s["total_cached_input_tokens"],s["total_reasoning_tokens"]),
                         (272906,11195,0,502))
        self.assertAlmostEqual(s["provider_spend_usd"],1.644405)
        self.assertEqual(s["provider_cost_coverage"],"18/18")
        for key in ("trial_weighted_pass_rate","case_balanced_pass_rate","trial_weighted_monthly_cost",
                    "case_balanced_monthly_cost","trial_weighted_total_cost_per_referral"):
            self.assertIsNone(s[key])

    def test_common_negative_identical_keys_and_counts(self):
        expected=[(14,4,0),(6,2,7),(9,0,4),(12,6,0),(10,8,0)]
        self.assertEqual(len(self.common),5)
        for row,values in zip(self.common,expected):
            self.assertEqual((row["passed"],row["invalid_model_output"],row["unsafe_booking_attempts"]),values)
            self.assertEqual((row["runs"],row["cases"]),(18,6))
            self.assertEqual(row["scope"],"NEGATIVE_SUBSET_STRESS_TEST_NOT_PRODUCTION")

    def test_spend_and_error_denominator(self):
        rows,vals=_spend(self.runs,self.batteries)
        self.assertEqual(Decimal(str(vals["selected_scored_run_spend"])),Decimal("2.13502002"))
        self.assertEqual(Decimal(str(vals["extra_charged_mistral_provider_error"])),Decimal("0.00031845"))
        self.assertEqual(Decimal(str(vals["recorded_selected_model_charges_including_error"])),Decimal("2.13533847"))
        self.assertEqual(rows[0]["scored_run_denominator"],278)
        self.assertEqual(rows[1]["scored_run_denominator"],0)

    def test_qwen_control_and_sensitivity(self):
        q1=[r for r in self.runs if r["experiment_id"]=="qwen3_30b_v1"]
        q2=[r for r in self.runs if r["experiment_id"]=="qwen3_30b_v2"]
        self.assertEqual({(r["case_id"],r["trial"]) for r in q1},
                         {(r["case_id"],r["trial"]) for r in q2})
        self.assertEqual((sum(r["passed"] for r in q1),sum(r["passed"] for r in q2)),(20,28))
        self.assertAlmostEqual((28-20)/52*100,15.3846153846)
        self.assertEqual(sensitivity_rates(.04),{"LOW":0.0,"BASE":.04,"HIGH":.14})

    def test_tool_calls_recomputed_and_price_tiers(self):
        calls=normalized_tool_calls(self.batteries)
        self.assertGreater(len(calls),0)
        self.assertTrue(all(c["provider_tokenization_status"]=="NOT_PROVIDER_TOKENIZATION" for c in calls))
        v2=[r for r in inventory() if r["prompt_version"]=="v2"]
        self.assertEqual({r["family"] for r in v2},{"OpenAI","Qwen","Mistral","Google","Anthropic"})
        self.assertEqual({r["team_price_tier"] for r in v2},{"lower_price","frontier"})


class OutputTests(unittest.TestCase):
    def test_output_scopes(self):
        summary=output_rows("model_cost_summary.csv")
        sensitivity=output_rows("sensitivity_analysis.csv")
        breakeven=output_rows("break_even_matrix.csv")
        bootstrap=output_rows("bootstrap_uncertainty.csv")
        pareto=output_rows("pareto_analysis.csv")
        self.assertEqual(len(summary),6)
        self.assertEqual(len({x["experiment_id"] for x in sensitivity}),4)
        self.assertEqual(len(breakeven),4)
        self.assertEqual(len({x["experiment_id"] for x in bootstrap}),4)
        self.assertEqual(len(pareto),4)
        claude=next(x for x in summary if x["scope"]=="FRONTIER_NEGATIVE_ONLY")
        self.assertEqual(claude["trial_weighted_monthly_cost"],"")

    def test_output_reconciliation(self):
        report=json.loads((D6/"outputs"/"cost_report.json").read_text(encoding="utf-8"))
        runs=output_rows("formal_runs_normalized.csv")
        spend=output_rows("evaluation_spend_reconciliation.csv")
        self.assertEqual((len(runs),report["selected_scored_run_count"],report["provider_cost_coverage"]),(278,278,"278/278"))
        self.assertEqual(spend[0]["value_usd"],"2.13502002")
        self.assertEqual(spend[1]["value_usd"],"0.00031845")
        self.assertEqual(spend[2]["value_usd"],"2.13533847")

    def test_fallback_and_pareto_math(self):
        self.assertEqual(FAILURE_COST_USD,Decimal(55)*Decimal(10)/Decimal(60))
        raw,feasible=break_even(.01,1.01)
        self.assertAlmostEqual(raw,1-1/float(FAILURE_COST_USD))
        self.assertEqual(raw,feasible)
        status=pareto_status([{"experiment_id":"A","cost":1,"pass_rate":.8},
                              {"experiment_id":"B","cost":2,"pass_rate":.7}])
        self.assertEqual(status,{"A":"PARETO_EFFICIENT","B":"DOMINATED"})

    def test_cluster_bootstrap_reproducible(self):
        rows=[{"case_id":"A","passed":True,"provider_cost_usd":.01},
              {"case_id":"B","passed":False,"provider_cost_usd":.02},
              {"case_id":"B","passed":False,"provider_cost_usd":.03}]
        self.assertEqual(bootstrap_metrics(rows,iterations=30,seed=6201),
                         bootstrap_metrics(rows,iterations=30,seed=6201))
        self.assertGreater(len(cluster_sample(rows,np.random.default_rng(5))),0)


if __name__=="__main__":
    unittest.main()
