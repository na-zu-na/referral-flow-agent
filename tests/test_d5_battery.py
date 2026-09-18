import unittest

from build_d5_comparison import validate_battery_set
from config import RunConfig
from run_d5_battery import (
    EXPECTED_NEGATIVE_RUNS,
    EXPECTED_RUNS,
    NEGATIVE_ONLY_RUNS,
    build_plan,
    charge,
)


class D5BatteryTests(unittest.TestCase):
    def test_plan_runs_all_cases_once_plus_two_extra_negative_trials(self):
        cases = [
            {"case_id": f"C{index:02d}", "negative_case": index < 6}
            for index in range(40)
        ]
        plan = build_plan(cases)
        negative_ids = {case["case_id"] for case in cases if case["negative_case"]}
        self.assertEqual(len(plan), EXPECTED_RUNS)
        self.assertEqual(len(set(plan)), EXPECTED_RUNS)
        self.assertEqual(sum(case_id in negative_ids for case_id, _ in plan), EXPECTED_NEGATIVE_RUNS)
        self.assertTrue(all(
            sorted(trial for case_id, trial in plan if case_id == negative_id) == [1, 2, 3]
            for negative_id in negative_ids
        ))

    def test_negative_only_plan_runs_each_of_six_negative_cases_three_times(self):
        cases = [
            {"case_id": f"C{index:02d}", "negative_case": index < 6}
            for index in range(40)
        ]
        plan = build_plan(cases, negative_only=True)
        negative_ids = {case["case_id"] for case in cases if case["negative_case"]}
        self.assertEqual(len(plan), NEGATIVE_ONLY_RUNS)
        self.assertEqual(len(set(plan)), NEGATIVE_ONLY_RUNS)
        self.assertEqual({case_id for case_id, _ in plan}, negative_ids)
        for case_id in negative_ids:
            self.assertEqual(
                sorted(trial for planned_id, trial in plan if planned_id == case_id),
                [1, 2, 3],
            )

    def test_unknown_provider_cost_is_recalculated_from_measured_tokens(self):
        settings = RunConfig(price_input_per_million=1.0, price_output_per_million=5.0)
        record = {
            "cost_source": "locally_calculated",
            "tokens_measured": True,
            "tokens_in": 1_000_000,
            "tokens_out": 100_000,
            "calculated_cost_usd": 0.0,
        }
        self.assertEqual(charge(record, settings), 1.5)

    def test_unmeasured_tokens_cannot_be_used_as_cost_evidence(self):
        settings = RunConfig(price_input_per_million=1.0, price_output_per_million=5.0)
        record = {
            "cost_source": "locally_calculated",
            "tokens_measured": False,
            "tokens_in": 0,
            "tokens_out": 0,
        }
        self.assertIsNone(charge(record, settings))

    @staticmethod
    def battery(model, prompt_version="v2"):
        identity = {
            "model": model,
            "operator": f"{prompt_version}:{model}",
            "prompt_version": prompt_version,
            "source_commit": "abc123",
            "descriptor_version": "v2",
            "call_mode": "parallel",
            "autonomy": "confirm",
            "temperature": 0.0,
            "planned_run_count": EXPECTED_RUNS,
            "negative_run_count": EXPECTED_NEGATIVE_RUNS,
            "local_token_prices_usd_per_million": {"input": 0.1, "output": 0.4},
            "public_config": {
                "backend": "live", "model": model, "prompt_version": prompt_version,
            },
        }
        return {
            "identity": identity,
            "keys": {(f"C{index:02d}", 1) for index in range(EXPECTED_RUNS)},
            "path": model,
        }

    def test_team_design_requires_five_v2_models_and_one_matching_v1(self):
        v2 = [self.battery(f"provider/model-{index}") for index in range(5)]
        v1 = self.battery("provider/model-0", "v1")
        selected, same_model = validate_battery_set(v2 + [v1])
        self.assertEqual(len(selected), 5)
        self.assertEqual(same_model["identity"]["model"], "provider/model-0")

    def test_four_v2_models_are_rejected_for_the_team_plan(self):
        batteries = [self.battery(f"provider/model-{index}") for index in range(4)]
        batteries.append(self.battery("provider/model-0", "v1"))
        with self.assertRaisesRegex(ValueError, "exactly five"):
            validate_battery_set(batteries)

    def test_each_battery_requires_a_distinct_operator(self):
        batteries = [self.battery(f"provider/model-{index}") for index in range(5)]
        batteries.append(self.battery("provider/model-0", "v1"))
        batteries[-1]["identity"]["operator"] = batteries[0]["identity"]["operator"]
        with self.assertRaisesRegex(ValueError, "each team member"):
            validate_battery_set(batteries)

    def test_v1_control_may_only_change_prompt_version(self):
        v2 = [self.battery(f"provider/model-{index}") for index in range(5)]
        v1 = self.battery("provider/model-0", "v1")
        v1["identity"]["public_config"]["max_turns"] = 99
        with self.assertRaisesRegex(ValueError, "more than prompt version"):
            validate_battery_set(v2 + [v1])

    def test_v1_control_uses_the_same_local_prices(self):
        v2 = [self.battery(f"provider/model-{index}") for index in range(5)]
        v1 = self.battery("provider/model-0", "v1")
        v1["identity"]["local_token_prices_usd_per_million"]["input"] = 9.9
        with self.assertRaisesRegex(ValueError, "different local token prices"):
            validate_battery_set(v2 + [v1])

    def test_legacy_52_identity_without_new_price_fields_is_accepted(self):
        batteries = [self.battery(f"provider/model-{index}") for index in range(5)]
        batteries.append(self.battery("provider/model-0", "v1"))
        for battery in batteries:
            identity = battery["identity"]
            identity["source_hashes"] = {"agent/loop.py": "hash"}
            identity.pop("negative_run_count")
            identity.pop("local_token_prices_usd_per_million")
        selected, same_model = validate_battery_set(batteries)
        self.assertEqual(len(selected), 5)
        self.assertEqual(same_model["identity"]["model"], "provider/model-0")

if __name__ == "__main__":
    unittest.main()
