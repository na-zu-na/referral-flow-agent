import unittest

from guardrails import ConfirmationRequired, GuardrailState, GuardrailStop


def tool_call(call_id, name, arguments=None):
    return {"id": call_id, "name": name, "arguments": arguments or {}}


class GuardrailTests(unittest.TestCase):
    def test_state_is_isolated_per_run(self):
        first = GuardrailState()
        second = GuardrailState()
        first.prepare_turn([tool_call("c1", "custom", {"value": 1})])

        self.assertEqual(first.turns, 1)
        self.assertEqual(second.turns, 0)
        self.assertEqual(second.seen_actions, set())

    def test_step_cap_stops_the_next_turn_loudly(self):
        state = GuardrailState(max_turns=2)
        state.prepare_turn([tool_call("c1", "custom", {"value": 1})])
        state.prepare_turn([tool_call("c2", "custom", {"value": 2})])

        with self.assertRaises(GuardrailStop) as caught:
            state.prepare_turn([tool_call("c3", "custom", {"value": 3})])

        self.assertEqual(caught.exception.code, "STEP_LIMIT_REACHED")
        self.assertTrue(caught.exception.to_event()["terminal"])
        self.assertEqual(state.turns, 2)

    def test_budget_ceiling_records_measured_usage(self):
        state = GuardrailState(max_tokens=10)
        state.add_tokens(input_tokens=6, output_tokens=4)
        self.assertEqual(state.tokens_total, 10)

        with self.assertRaises(GuardrailStop) as caught:
            state.add_tokens(input_tokens=1)

        self.assertEqual(caught.exception.code, "BUDGET_LIMIT_REACHED")
        self.assertEqual(state.tokens_total, 11)

    def test_duplicate_detection_uses_canonical_nested_json(self):
        state = GuardrailState()
        state.prepare_turn(
            [tool_call("c1", "custom", {"outer": {"b": 2, "a": 1}})]
        )

        with self.assertRaises(GuardrailStop) as caught:
            state.prepare_turn(
                [tool_call("c2", "custom", {"outer": {"a": 1, "b": 2}})]
            )

        self.assertEqual(caught.exception.code, "DUPLICATE_ACTION_BLOCKED")

    def test_criteria_and_patient_can_run_together_after_referral(self):
        state = GuardrailState()
        referral = tool_call("c1", "get_referral", {"referral_id": "REF-5602"})
        state.prepare_turn([referral])
        state.record_observation(referral, {"ok": True, "data": {}})

        state.prepare_turn(
            [
                tool_call(
                    "c2",
                    "check_referral_criteria",
                    {"referral_id": "REF-5602", "specialty": "OPH"},
                ),
                tool_call("c3", "lookup_patient", {"patient_id": "P-1180"}),
            ]
        )

        self.assertEqual(state.turns, 2)

    def test_failed_observation_does_not_unlock_dependency(self):
        state = GuardrailState()
        referral = tool_call("c1", "get_referral", {"referral_id": "REF-9999"})
        state.prepare_turn([referral])
        state.record_observation(
            referral, {"ok": False, "error": {"code": "NOT_FOUND", "message": "Missing"}}
        )

        with self.assertRaises(GuardrailStop) as caught:
            state.prepare_turn(
                [
                    tool_call(
                        "c2",
                        "check_referral_criteria",
                        {"referral_id": "REF-9999", "specialty": "OPH"},
                    )
                ]
            )

        self.assertEqual(caught.exception.code, "DEPENDENCY_VIOLATION")

    def test_hostile_criteria_observation_stops_the_run(self):
        state = GuardrailState()
        referral = tool_call("r1", "get_referral", {"referral_id": "REF-5703"})
        state.prepare_turn([referral])
        state.record_observation(referral, {"ok": True, "data": {}})
        call = tool_call(
            "c1",
            "check_referral_criteria",
            {"referral_id": "REF-5703", "specialty": "OPH"},
        )
        state.prepare_turn([call])

        with self.assertRaises(GuardrailStop) as caught:
            state.record_observation(
                call,
                {"ok": True, "data": {"hostile_input_detected": True}},
            )

        self.assertEqual(caught.exception.code, "HOSTILE_INPUT_DETECTED")
        self.assertEqual(state.events[-1]["blocked_call_id"], "c1")

        with self.assertRaises(GuardrailStop) as repeated:
            state.prepare_turn([tool_call("later", "get_system_date")])

        self.assertEqual(repeated.exception.code, "HOSTILE_INPUT_DETECTED")
        self.assertNotIn("later", state.prepared_calls)
        self.assertEqual(len(state.events), 1)

    def test_unprepared_or_repeated_observation_is_rejected(self):
        state = GuardrailState()
        call = tool_call("c1", "custom")

        with self.assertRaises(GuardrailStop) as unprepared:
            state.record_observation(call, {"ok": True, "data": {}})
        self.assertEqual(unprepared.exception.code, "UNEXPECTED_TOOL_OBSERVATION")

        state = GuardrailState()
        state.prepare_turn([call])
        state.record_observation(call, {"ok": True, "data": {}})
        with self.assertRaises(GuardrailStop) as repeated:
            state.record_observation(call, {"ok": True, "data": {}})
        self.assertEqual(repeated.exception.code, "UNEXPECTED_TOOL_OBSERVATION")

    def test_dependent_call_in_same_turn_is_blocked(self):
        state = GuardrailState()

        with self.assertRaises(GuardrailStop) as caught:
            state.prepare_turn(
                [
                    tool_call("c1", "get_referral", {"referral_id": "REF-5602"}),
                    tool_call("c2", "lookup_patient", {"patient_id": "P-1180"}),
                ]
            )

        self.assertEqual(caught.exception.code, "DEPENDENCY_VIOLATION")

    def test_book_slot_must_run_alone(self):
        state = GuardrailState()
        state.completed_tools.update(
            {"check_referral_criteria", "lookup_patient", "get_clinic_slots"}
        )

        with self.assertRaises(GuardrailStop) as caught:
            state.prepare_turn(
                [
                    tool_call("c1", "book_slot", {"referral_id": "REF-5602"}),
                    tool_call("c2", "get_system_date"),
                ]
            )

        self.assertEqual(caught.exception.code, "DEPENDENCY_VIOLATION")

    def test_confirm_autonomy_ignores_model_supplied_confirmation(self):
        state = GuardrailState(autonomy="confirm")
        call = tool_call("c1", "book_slot", {"confirmed": True})
        state.completed_tools.update(
            {"check_referral_criteria", "lookup_patient", "get_clinic_slots"}
        )
        state.prepare_turn([call])

        with self.assertRaises(ConfirmationRequired) as caught:
            state.check_autonomy(call)

        event = caught.exception.to_event()
        self.assertFalse(event["terminal"])
        self.assertEqual(event["code"], "HUMAN_CONFIRMATION_REQUIRED")

        state.approve("c1")
        state.check_autonomy(call)
        self.assertEqual(state.events[-1]["code"], "AUTONOMY_GATE_PASSED")

    def test_suggest_blocks_and_act_allows(self):
        call = tool_call("c1", "book_slot")
        suggest = GuardrailState(autonomy="suggest")
        act = GuardrailState(autonomy="act")
        for state in (suggest, act):
            state.completed_tools.update(
                {"check_referral_criteria", "lookup_patient", "get_clinic_slots"}
            )
            state.prepare_turn([call])

        with self.assertRaises(GuardrailStop) as caught:
            suggest.check_autonomy(call)
        self.assertEqual(caught.exception.code, "AUTONOMY_SUGGEST_ONLY")

        act.check_autonomy(call)
        self.assertEqual(act.events[-1]["code"], "AUTONOMY_GATE_PASSED")


if __name__ == "__main__":
    unittest.main()
