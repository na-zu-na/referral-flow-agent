import unittest

from experiments.d7_failures import DEPENDENCY_RULE, dependency_prompts, run_all


class D7FailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_all(write_results=False)

    def test_core_distribution_sets_evidence_based_cap(self):
        distribution = self.result["turn_distribution"]
        self.assertEqual(distribution["cases"], 40)
        self.assertEqual(distribution["passed"], 40)
        self.assertEqual(distribution["step_cap_hits"], 0)
        self.assertEqual(
            self.result["recommended_step_cap"], distribution["worst_turns"] + 1
        )

    def test_loop_failure_is_caught_earlier_after_fix(self):
        failure = self.result["failure_1"]
        self.assertEqual(failure["broken"]["stopped_by"], "STEP_LIMIT_REACHED")
        self.assertEqual(failure["fixed"]["stopped_by"], "DUPLICATE_ACTION_BLOCKED")
        self.assertFalse(failure["broken"]["experiment_passed"])
        self.assertTrue(failure["fixed"]["experiment_passed"])
        self.assertLess(failure["fixed"]["turns"], failure["broken"]["turns"])
        self.assertLess(failure["fixed"]["cost_usd"], failure["broken"]["cost_usd"])

    def test_prompt_fix_recovers_correct_case(self):
        failure = self.result["failure_2"]
        self.assertFalse(failure["broken"]["case_passed"])
        self.assertEqual(failure["broken"]["stopped_by"], "DEPENDENCY_VIOLATION")
        self.assertTrue(failure["fixed"]["case_passed"])
        self.assertEqual(failure["fixed"]["trigger"], "no_slot_in_window")

    def test_prompt_failure_deletes_exactly_one_rule(self):
        working, broken = dependency_prompts()
        self.assertEqual(working.count(DEPENDENCY_RULE), 1)
        self.assertEqual(broken, working.replace(DEPENDENCY_RULE, ""))
        control = self.result["failure_2"]["controlled_variable"]
        self.assertEqual(control["same_case"], "REF-5697")
        self.assertEqual(control["same_descriptor_version"], "v2")
        self.assertTrue(control["same_controller_tools_and_guardrails"])
        self.assertEqual(control["deleted_characters"], len(DEPENDENCY_RULE))

    def test_deleting_dedup_does_not_change_ordinary_core_paths(self):
        regression = self.result["dedup_regression"]
        self.assertEqual(regression["working_pass_rate"], 1.0)
        self.assertEqual(regression["dedup_deleted_pass_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
