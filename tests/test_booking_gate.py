import unittest

from guardrails import (
    ConfirmationRequired,
    GuardrailState,
    GuardrailStop,
    authorize_booking,
    check_booking_allowed,
)
from tools import book_slot, call_tool


def call(call_id, name, arguments):
    return {"id": call_id, "name": name, "arguments": arguments}


def execute(state, calls):
    state.prepare_turn(calls)
    for item in calls:
        result = call_tool(item["name"], item["arguments"])
        state.record_observation(item, result)
    return result


def booking_state(referral_id, patient_id, specialty):
    state = GuardrailState(autonomy="confirm")
    execute(state, [call("c1", "get_referral", {"referral_id": referral_id})])
    criteria_call = call(
        "c2",
        "check_referral_criteria",
        {"referral_id": referral_id, "specialty": specialty},
    )
    patient_call = call("c3", "lookup_patient", {"patient_id": patient_id})
    execute(state, [criteria_call, patient_call])
    criteria = state.observations["c2"]["result"]["data"]
    slot_call = call(
        "c4",
        "get_clinic_slots",
        {
            "specialty": specialty,
            "band": criteria["band"],
            "window_start": criteria["window_start"],
            "window_end": criteria["window_end"],
            "limit": 5,
        },
    )
    execute(state, [slot_call])
    slots = state.observations["c4"]["result"]["data"]["slots"]
    return state, criteria, slots


def prepare_booking(state, referral_id, specialty, band, slot):
    item = call(
        "c5",
        "book_slot",
        {
            "referral_id": referral_id,
            "clinic": slot["clinic"],
            "specialty": specialty,
            "band": band,
            "date": slot["date"],
            "time": slot["time"],
        },
    )
    state.prepare_turn([item])
    return item


class BookingGateTests(unittest.TestCase):
    def test_safe_booking_requires_trusted_confirmation_then_passes(self):
        state, criteria, slots = booking_state("REF-5602", "P-1180", "OPH")
        booking = prepare_booking(state, "REF-5602", "OPH", criteria["band"], slots[0])

        result = check_booking_allowed(booking["arguments"], state, booking["id"])
        self.assertFalse(result["allowed"])
        self.assertEqual(
            [reason["code"] for reason in result["reasons"]],
            ["HUMAN_CONFIRMATION_REQUIRED"],
        )
        with self.assertRaises(ConfirmationRequired):
            authorize_booking(booking, state)

        state.approve(booking["id"])
        self.assertTrue(authorize_booking(booking, state)["allowed"])
        self.assertEqual(state.events[-1]["code"], "BOOKING_GATE_PASSED")

    def test_book_slot_executes_only_through_authorized_call_tool(self):
        state, criteria, slots = booking_state("REF-5602", "P-1180", "OPH")
        booking = prepare_booking(state, "REF-5602", "OPH", criteria["band"], slots[0])

        blocked = call_tool("book_slot", booking["arguments"])
        self.assertEqual(blocked["error"]["code"], "BOOKING_AUTHORIZATION_REQUIRED")
        with self.assertRaises(ConfirmationRequired):
            call_tool(
                "book_slot",
                booking["arguments"],
                state=state,
                call_id=booking["id"],
            )

        state.approve(booking["id"])
        result = call_tool(
            "book_slot",
            booking["arguments"],
            state=state,
            call_id=booking["id"],
        )
        state.record_observation(booking, result)

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["capacity_remaining_after"], 1)
        self.assertEqual(state.bookings, [result["data"]])

    def test_raw_book_slot_cannot_bypass_booking_gate(self):
        state, criteria, slots = booking_state("REF-5590", "P-1192", "OPH")
        booking = prepare_booking(state, "REF-5590", "OPH", criteria["band"], slots[0])

        with self.assertRaises(GuardrailStop) as caught:
            book_slot(
                **booking["arguments"],
                _state=state,
                _call_id=booking["id"],
            )

        self.assertEqual(caught.exception.code, "BOOKING_GATE_NOT_SATISFIED")
        self.assertEqual(state.bookings, [])

    def test_simulated_booking_does_not_modify_fixture_or_other_runs(self):
        first, criteria, slots = booking_state("REF-5602", "P-1180", "OPH")
        booking = prepare_booking(first, "REF-5602", "OPH", criteria["band"], slots[0])
        first.approve(booking["id"])
        result = call_tool(
            "book_slot", booking["arguments"], state=first, call_id=booking["id"]
        )
        self.assertTrue(result["ok"])

        second, second_criteria, second_slots = booking_state("REF-5602", "P-1180", "OPH")
        second_booking = prepare_booking(
            second, "REF-5602", "OPH", second_criteria["band"], second_slots[0]
        )
        second.approve(second_booking["id"])
        second_result = call_tool(
            "book_slot",
            second_booking["arguments"],
            state=second,
            call_id=second_booking["id"],
        )

        self.assertTrue(second_result["ok"])
        self.assertEqual(second_result["data"]["capacity_remaining_after"], 1)

    def test_same_referral_cannot_be_booked_twice_in_one_run(self):
        state, criteria, slots = booking_state("REF-5602", "P-1180", "OPH")
        first = prepare_booking(state, "REF-5602", "OPH", criteria["band"], slots[0])
        state.approve(first["id"])
        first_result = call_tool(
            "book_slot", first["arguments"], state=state, call_id=first["id"]
        )
        state.record_observation(first, first_result)

        second = call(
            "c6",
            "book_slot",
            {
                "referral_id": "REF-5602",
                "clinic": slots[1]["clinic"],
                "specialty": "OPH",
                "band": criteria["band"],
                "date": slots[1]["date"],
                "time": slots[1]["time"],
            },
        )
        state.prepare_turn([second])
        state.approve(second["id"])

        with self.assertRaises(GuardrailStop) as caught:
            call_tool(
                "book_slot", second["arguments"], state=state, call_id=second["id"]
            )
        self.assertIn("DUPLICATE_BOOKING", caught.exception.event["message"])

    def test_exhausted_simulated_capacity_is_blocked(self):
        state, criteria, slots = booking_state("REF-5602", "P-1180", "OPH")
        booking = prepare_booking(state, "REF-5602", "OPH", criteria["band"], slots[0])
        slot_key = "|".join(
            booking["arguments"][key]
            for key in ("clinic", "specialty", "band", "date", "time")
        )
        state.slot_capacity_used[slot_key] = slots[0]["capacity_remaining"]
        state.approve(booking["id"])

        with self.assertRaises(GuardrailStop) as caught:
            call_tool(
                "book_slot",
                booking["arguments"],
                state=state,
                call_id=booking["id"],
            )
        self.assertIn("SLOT_FULL", caught.exception.event["message"])

    def test_red_flag_blocks_booking_even_when_a_slot_exists(self):
        state, criteria, slots = booking_state("REF-5590", "P-1192", "OPH")
        booking = prepare_booking(state, "REF-5590", "OPH", criteria["band"], slots[0])
        state.approve(booking["id"])

        result = check_booking_allowed(booking["arguments"], state, booking["id"])
        self.assertIn("RED_FLAG_DETECTED", {reason["code"] for reason in result["reasons"]})
        with self.assertRaises(GuardrailStop) as caught:
            authorize_booking(booking, state)
        self.assertEqual(caught.exception.code, "BOOKING_GATE_NOT_SATISFIED")

    def test_missing_test_and_wrong_department_are_blocked(self):
        incomplete, criteria, slots = booking_state("REF-5614", "P-1227", "OPH")
        booking = prepare_booking(incomplete, "REF-5614", "OPH", criteria["band"], slots[0])
        codes = {
            reason["code"]
            for reason in check_booking_allowed(
                booking["arguments"], incomplete, booking["id"], False
            )["reasons"]
        }
        self.assertIn("MANDATORY_TESTS_MISSING", codes)

        wrong, criteria, slots = booking_state("REF-5671", "P-1241", "OPH")
        booking = prepare_booking(wrong, "REF-5671", "OPH", criteria["band"], slots[0])
        codes = {
            reason["code"]
            for reason in check_booking_allowed(
                booking["arguments"], wrong, booking["id"], False
            )["reasons"]
        }
        self.assertIn("SPECIALTY_MISMATCH", codes)

    def test_future_same_specialty_appointment_is_duplicate(self):
        state, criteria, slots = booking_state("REF-5684", "P-1204", "OPH")
        booking = prepare_booking(state, "REF-5684", "OPH", criteria["band"], slots[0])

        codes = {
            reason["code"]
            for reason in check_booking_allowed(
                booking["arguments"], state, booking["id"], False
            )["reasons"]
        }
        self.assertIn("DUPLICATE_APPOINTMENT", codes)

    def test_past_same_specialty_appointment_is_not_duplicate(self):
        state, criteria, slots = booking_state("REF-5645", "P-1215", "ORT")
        booking = prepare_booking(state, "REF-5645", "ORT", criteria["band"], slots[0])
        state.approve(booking["id"])

        self.assertTrue(check_booking_allowed(booking["arguments"], state, booking["id"])["allowed"])

    def test_unobserved_wrong_band_slot_is_blocked(self):
        state, criteria, slots = booking_state("REF-5602", "P-1180", "OPH")
        wrong_slot = dict(slots[0], band="urgent")
        booking = prepare_booking(state, "REF-5602", "OPH", "urgent", wrong_slot)

        codes = {
            reason["code"]
            for reason in check_booking_allowed(
                booking["arguments"], state, booking["id"], False
            )["reasons"]
        }
        self.assertIn("URGENCY_BAND_MISMATCH", codes)
        self.assertIn("SLOT_NOT_OBSERVED", codes)

    def test_model_cannot_supply_safety_or_confirmation_flags(self):
        state = GuardrailState()
        result = check_booking_allowed(
            {
                "referral_id": "REF-5602",
                "clinic": "OPH-C2",
                "specialty": "OPH",
                "band": "routine",
                "date": "2026-10-14",
                "time": "11:20",
                "confirmed": True,
            },
            state,
        )

        self.assertEqual(
            [reason["code"] for reason in result["reasons"]],
            ["INVALID_BOOKING_ARGUMENTS"],
        )

    def test_incomplete_safety_evidence_fails_closed(self):
        state, criteria, slots = booking_state("REF-5602", "P-1180", "OPH")
        booking = prepare_booking(state, "REF-5602", "OPH", criteria["band"], slots[0])
        del state.observations["c2"]["result"]["data"]["red_flags_detected"]

        codes = {
            reason["code"]
            for reason in check_booking_allowed(
                booking["arguments"], state, booking["id"], False
            )["reasons"]
        }

        self.assertIn("INVALID_CRITERIA_EVIDENCE", codes)

    def test_missing_evidence_and_unprepared_call_are_blocked(self):
        result = check_booking_allowed(
            {
                "referral_id": "REF-5602",
                "clinic": "OPH-C2",
                "specialty": "OPH",
                "band": "routine",
                "date": "2026-10-14",
                "time": "11:20",
            },
            GuardrailState(),
            "not-prepared",
            False,
        )
        codes = {reason["code"] for reason in result["reasons"]}

        self.assertIn("BOOKING_CALL_NOT_PREPARED", codes)
        self.assertIn("MISSING_REFERRAL_EVIDENCE", codes)
        self.assertIn("MISSING_CRITERIA_EVIDENCE", codes)
        self.assertIn("MISSING_PATIENT_EVIDENCE", codes)
        self.assertIn("SLOT_NOT_OBSERVED", codes)


if __name__ == "__main__":
    unittest.main()
