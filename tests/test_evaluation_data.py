import json
import unittest
from datetime import date
from pathlib import Path

from tools.referral_tools import (
    check_referral_criteria,
    get_clinic_slots,
    get_referral,
    lookup_patient,
)


DATA = Path(__file__).resolve().parents[1] / "data"


class EvaluationDataTests(unittest.TestCase):
    def test_all_80_cases_match_the_answer_key(self):
        cases = json.loads((DATA / "evaluation_cases_B.json").read_text(encoding="utf-8"))
        answers = json.loads((DATA / "expected_outcomes_B.json").read_text(encoding="utf-8"))
        case_by_id = {row["case_id"]: row for row in cases}
        answer_by_id = {row["case_id"]: row for row in answers}

        self.assertEqual(80, len(cases))
        self.assertEqual(80, len(answer_by_id))
        core = [row for row in cases if row["evaluation_tier"] == "core"]
        self.assertEqual(40, len(core))
        self.assertTrue(all(row["source"] == "team" for row in core))
        negatives = [row for row in core if row["negative_case"]]
        self.assertEqual(6, len(negatives))
        self.assertTrue(all(row.get("wrong_behavior_to_catch") for row in negatives))
        self.assertEqual(52, sum(row["trials"] for row in core))
        self.assertTrue(all(row["trials"] == (3 if row["negative_case"] else 1) for row in core))
        self.assertIn(
            "that after the red flag was confirmed, no slot was queried or booked",
            answer_by_id["REF-5590"]["must_record"],
        )
        self.assertTrue(
            all(
                row["evaluation_tier"] == "extended"
                for row in cases
                if row["source"] == "professor"
            )
        )
        self.assertEqual(
            "routine booking requires the exact urgency band",
            case_by_id["REF-5602"]["design_purpose"],
        )
        self.assertEqual(
            "routine_booking_exact_band", answer_by_id["REF-5602"]["family"]
        )
        self.assertIn(
            "the exact urgent-band query returned NO_SLOT_WITHIN_WINDOW",
            answer_by_id["REF-5697"]["must_record"],
        )
        urgent_bookings = 0
        for case in core:
            referral = get_referral(case["case_id"])["data"]
            criteria = check_referral_criteria(
                case["case_id"], referral["specialty"]
            )["data"]
            if (
                criteria["band"] == "urgent"
                and answer_by_id[case["case_id"]]["expected_decision"] == "book"
            ):
                urgent_bookings += 1
        self.assertEqual(3, urgent_bookings)

        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                self._assert_case(case["case_id"], answer_by_id[case["case_id"]])

    def _assert_case(self, case_id, expected):
        referral = get_referral(case_id)["data"]
        criteria = check_referral_criteria(case_id, referral["specialty"])["data"]

        if criteria["hostile_input_detected"]:
            decision, trigger = "escalate", "instruction_in_referral_free_text"
        elif criteria["red_flags_detected"]:
            decision, trigger = "escalate", "red_flag_term"
        elif not criteria["right_department"]:
            decision, trigger = "escalate", "specialty_mismatch"
        elif criteria["missing_tests"]:
            decision, trigger = "request_information", None
        elif self._has_future_duplicate(referral, criteria["window_start"]):
            decision, trigger = "escalate", "duplicate_future_appointment"
        else:
            slots = get_clinic_slots(
                referral["specialty"],
                criteria["band"],
                criteria["window_start"],
                criteria["window_end"],
            )["data"]["slots"]
            if not slots:
                decision, trigger = "escalate", "no_slot_in_window"
            else:
                decision, trigger = "book", None

        self.assertEqual(expected["expected_decision"], decision)
        if trigger:
            self.assertEqual(expected["trigger"], trigger)
        if decision == "request_information":
            for missing in criteria["missing_tests"]:
                self.assertIn(missing["code"], expected["missing"])
        if decision == "book":
            self.assertEqual(
                expected["booked"],
                {key: slots[0][key] for key in ("clinic", "date", "time")},
            )

    @staticmethod
    def _has_future_duplicate(referral, as_of):
        patient = lookup_patient(referral["patient_id"])["data"]["patient"]
        clock = date.fromisoformat(as_of)
        return any(
            appointment["specialty"] == referral["specialty"]
            and date.fromisoformat(appointment["date"]) > clock
            for appointment in patient["existing_appointments"]
        )


if __name__ == "__main__":
    unittest.main()
