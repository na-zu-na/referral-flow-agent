"""Evidence-based safety gate for the simulated booking action."""

from __future__ import annotations

from datetime import date
from typing import Any

from .core import GuardrailState

_BOOKING_ARGUMENTS = {
    "referral_id",
    "clinic",
    "specialty",
    "band",
    "date",
    "time",
}


def check_booking_allowed(
    arguments: dict[str, Any],
    state: GuardrailState,
    call_id: str | None = None,
    require_confirmation: bool = True,
) -> dict[str, Any]:
    """Return every reason a proposed booking is unsafe or unsupported."""
    reasons: list[dict[str, str]] = []

    def reject(code: str, message: str) -> None:
        if not any(reason["code"] == code for reason in reasons):
            reasons.append({"code": code, "message": message})

    if not isinstance(arguments, dict) or set(arguments) != _BOOKING_ARGUMENTS:
        reject(
            "INVALID_BOOKING_ARGUMENTS",
            "Booking requires exactly referral_id, clinic, specialty, band, date, and time.",
        )
        return _gate_result(reasons)
    if not all(isinstance(value, str) and value for value in arguments.values()):
        reject("INVALID_BOOKING_ARGUMENTS", "Every booking argument must be a non-empty string.")
        return _gate_result(reasons)

    prepared_id = _prepared_booking_id(arguments, state, call_id)
    if prepared_id is None:
        reject("BOOKING_CALL_NOT_PREPARED", "The booking call was not prepared by the Agent Controller.")

    referral = _find_data(
        state,
        "get_referral",
        lambda call, data: call["arguments"].get("referral_id") == arguments["referral_id"]
        and data.get("referral_id") == arguments["referral_id"],
    )
    if referral is None:
        reject("MISSING_REFERRAL_EVIDENCE", "No matching successful referral observation exists.")
    elif referral.get("specialty") != arguments["specialty"]:
        reject("SPECIALTY_MISMATCH", "Booking specialty differs from the referral specialty.")

    criteria = _find_data(
        state,
        "check_referral_criteria",
        lambda call, data: call["arguments"].get("referral_id") == arguments["referral_id"]
        and call["arguments"].get("specialty") == arguments["specialty"],
    )
    if criteria is None:
        reject("MISSING_CRITERIA_EVIDENCE", "No matching successful criteria observation exists.")
    else:
        if criteria.get("hostile_input_detected") is not False:
            reject("HOSTILE_INPUT_DETECTED", "Referral text is hostile or was not proven safe.")
        red_flags = criteria.get("red_flags_detected")
        if not isinstance(red_flags, list):
            reject("INVALID_CRITERIA_EVIDENCE", "Red-flag evidence is missing or invalid.")
        elif red_flags:
            reject("RED_FLAG_DETECTED", "Referral contains a specialty-specific red flag.")
        if criteria.get("right_department") is not True:
            reject("SPECIALTY_MISMATCH", "Referral was not proven suitable for this department.")
        missing_tests = criteria.get("missing_tests")
        if not isinstance(missing_tests, list):
            reject("INVALID_CRITERIA_EVIDENCE", "Mandatory-test evidence is missing or invalid.")
        elif missing_tests:
            reject("MANDATORY_TESTS_MISSING", "Referral has missing mandatory tests.")
        if criteria.get("band") != arguments["band"]:
            reject("URGENCY_BAND_MISMATCH", "Booking band differs from the assessed urgency band.")
        if not _inside_window(arguments["date"], criteria):
            reject("SLOT_OUTSIDE_WINDOW", "Booking date is outside the assessed clinical window.")

    patient_id = referral.get("patient_id") if referral else None
    patient_bundle = _find_data(
        state,
        "lookup_patient",
        lambda call, data: call["arguments"].get("patient_id") == patient_id
        and isinstance(data.get("patient"), dict)
        and data["patient"].get("patient_id") == patient_id,
    ) if patient_id else None
    if patient_bundle is None:
        reject("MISSING_PATIENT_EVIDENCE", "No matching successful patient observation exists.")
    elif criteria is not None:
        duplicate = _has_future_duplicate(
            patient_bundle["patient"].get("existing_appointments"),
            arguments["specialty"],
            criteria.get("window_start"),
        )
        if duplicate is None:
            reject("INVALID_PATIENT_EVIDENCE", "Appointment history is missing or invalid.")
        elif duplicate:
            reject("DUPLICATE_APPOINTMENT", "Patient already has a future appointment in this specialty.")

    selected_slot = _find_slot(arguments, state)
    if selected_slot is None:
        reject("SLOT_NOT_OBSERVED", "The selected slot was not returned by a matching slot query.")
    else:
        capacity = selected_slot.get("capacity_remaining", 0)
        used = state.slot_capacity_used.get(_slot_key(arguments), 0)
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity - used <= 0:
            reject("SLOT_FULL", "The selected slot has no remaining capacity.")

    if any(booking.get("referral_id") == arguments["referral_id"] for booking in state.bookings):
        reject("DUPLICATE_BOOKING", "This referral was already booked during the current run.")

    if require_confirmation:
        if state.autonomy == "suggest":
            reject("AUTONOMY_SUGGEST_ONLY", "Suggest autonomy cannot execute bookings.")
        elif state.autonomy == "confirm" and prepared_id not in state.approved_calls:
            reject("HUMAN_CONFIRMATION_REQUIRED", "A trusted human has not confirmed this booking.")

    return _gate_result(reasons)


def authorize_booking(call: dict[str, Any], state: GuardrailState) -> dict[str, Any]:
    """Block unsafe calls, then apply autonomy and confirmation controls."""
    call_id = call.get("id") if isinstance(call, dict) else None
    arguments = call.get("arguments") if isinstance(call, dict) else None
    safety = check_booking_allowed(arguments, state, call_id, require_confirmation=False)
    if not safety["allowed"]:
        state.block(
            "BOOKING_GATE_NOT_SATISFIED",
            "; ".join(reason["code"] for reason in safety["reasons"]),
            call_id,
        )

    state.check_autonomy(call)
    final = check_booking_allowed(arguments, state, call_id, require_confirmation=True)
    if not final["allowed"]:
        state.block(
            "BOOKING_GATE_NOT_SATISFIED",
            "; ".join(reason["code"] for reason in final["reasons"]),
            call_id,
        )
    state.record_event("BOOKING_GATE_PASSED", "All booking conditions were satisfied.", call_id)
    return final


def _prepared_booking_id(
    arguments: dict[str, Any], state: GuardrailState, call_id: str | None
) -> str | None:
    if call_id is not None:
        call = state.prepared_calls.get(call_id)
        return call_id if call == {"id": call_id, "name": "book_slot", "arguments": arguments} else None
    matches = [
        prepared_id
        for prepared_id, call in state.prepared_calls.items()
        if call.get("name") == "book_slot" and call.get("arguments") == arguments
    ]
    return matches[0] if len(matches) == 1 else None


def _find_data(state: GuardrailState, tool: str, predicate) -> dict[str, Any] | None:
    for observation in state.observations.values():
        call = observation["call"]
        result = observation["result"]
        data = result.get("data")
        if call["name"] == tool and result.get("ok") is True and isinstance(data, dict):
            if predicate(call, data):
                return data
    return None


def _find_slot(arguments: dict[str, Any], state: GuardrailState) -> dict[str, Any] | None:
    identity = ("clinic", "specialty", "band", "date", "time")
    for observation in state.observations.values():
        call = observation["call"]
        result = observation["result"]
        data = result.get("data")
        if call["name"] != "get_clinic_slots" or result.get("ok") is not True:
            continue
        if not isinstance(data, dict) or not isinstance(data.get("slots"), list):
            continue
        for slot in data["slots"]:
            if isinstance(slot, dict) and all(slot.get(key) == arguments[key] for key in identity):
                return slot
    return None


def _inside_window(value: str, criteria: dict[str, Any]) -> bool:
    try:
        selected = date.fromisoformat(value)
        start = date.fromisoformat(criteria["window_start"])
        end = date.fromisoformat(criteria["window_end"])
    except (KeyError, TypeError, ValueError):
        return False
    return start <= selected <= end


def _has_future_duplicate(
    appointments: Any, specialty: str, as_of: Any
) -> bool | None:
    if not isinstance(appointments, list) or not isinstance(as_of, str):
        return None
    try:
        clock = date.fromisoformat(as_of)
    except ValueError:
        return None
    for appointment in appointments:
        if not isinstance(appointment, dict):
            return None
        if appointment.get("specialty") != specialty:
            continue
        try:
            appointment_date = date.fromisoformat(appointment["date"])
        except (KeyError, TypeError, ValueError):
            return None
        if appointment_date > clock:
            return True
    return False


def _gate_result(reasons: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "allowed": not reasons,
        "code": "BOOKING_ALLOWED" if not reasons else "BOOKING_GATE_NOT_SATISFIED",
        "reasons": reasons,
    }


def _slot_key(values: dict[str, Any]) -> str:
    return "|".join(
        str(values[key]) for key in ("clinic", "specialty", "band", "date", "time")
    )
