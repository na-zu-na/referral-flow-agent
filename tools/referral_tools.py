"""Read-only tools for outpatient referral coordination."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from .data_store import DataStoreError, load_object, load_table
from .registry import failure, success

_HOSTILE_PATTERNS = (
    re.compile(r"\bsystem\s+(?:note|message|instruction)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:ignore|override|bypass|skip)\b.{0,80}"
        r"\b(?:rule|instruction|check|test|protocol)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:check_referral_criteria|tool)\s+(?:returned|result|output)\b",
        re.IGNORECASE,
    ),
)


def get_referral(referral_id: str) -> dict[str, Any]:
    """Return one referral exactly as stored in the fixture."""
    if not isinstance(referral_id, str) or not referral_id.strip():
        return failure("INVALID_REFERRAL_ID", "referral_id must be a non-empty string.")
    try:
        referral = next(
            (row for row in load_table("referrals") if row.get("referral_id") == referral_id),
            None,
        )
    except DataStoreError as exc:
        return _data_failure(exc)
    if referral is None:
        return failure("REFERRAL_NOT_FOUND", f"Referral {referral_id} does not exist.")
    return success(referral)


def get_system_date() -> dict[str, Any]:
    """Return the fixed clock used for every Problem B booking window."""
    try:
        value = load_object("as_of").get("as_of")
        _parse_date(value)
    except DataStoreError as exc:
        return _data_failure(exc)
    except (TypeError, ValueError):
        return failure("DATA_INVALID_RECORD", "as_of.json must contain a valid ISO date.")
    return success({"as_of": value})


def check_referral_criteria(referral_id: str, specialty: str) -> dict[str, Any]:
    """Report protocol facts; the Agent remains responsible for the decision."""
    if not isinstance(referral_id, str) or not referral_id.strip():
        return failure("INVALID_REFERRAL_ID", "referral_id must be a non-empty string.")
    if not isinstance(specialty, str) or not specialty.strip():
        return failure("INVALID_SPECIALTY", "specialty must be a non-empty string.")

    try:
        referrals = load_table("referrals")
        specialties = load_table("specialties")
        bands = load_table("urgency_bands")
        clock = load_object("as_of").get("as_of")
    except DataStoreError as exc:
        return _data_failure(exc)

    referral = next((r for r in referrals if r.get("referral_id") == referral_id), None)
    if referral is None:
        return failure("REFERRAL_NOT_FOUND", f"Referral {referral_id} does not exist.")
    if referral.get("specialty") != specialty:
        return failure(
            "SPECIALTY_ARGUMENT_MISMATCH",
            f"Referral {referral_id} belongs to specialty {referral.get('specialty')!r}.",
        )
    protocol = next((s for s in specialties if s.get("code") == specialty), None)
    if protocol is None:
        return failure("SPECIALTY_NOT_FOUND", f"Specialty {specialty} does not exist.")

    text = referral.get("clinical_summary")
    if not isinstance(text, str):
        return failure("DATA_INVALID_RECORD", "clinical_summary must be a string.")
    lowered = text.lower()

    hostile_matches = [
        match.group(0)
        for pattern in _HOSTILE_PATTERNS
        if (match := pattern.search(text)) is not None
    ]
    red_flags = [
        term for term in protocol.get("red_flag_terms", []) if term.lower() in lowered
    ]
    department_terms = [
        term for term in protocol.get("treats", []) if term.lower() in lowered
    ]
    attached = set(referral.get("tests_attached") or [])
    missing_tests = [
        test
        for test in protocol.get("mandatory_tests", [])
        if test.get("code") not in attached
    ]

    routine = next((candidate for candidate in bands if candidate.get("band") == "routine"), None)
    if routine is None:
        return failure("DATA_INVALID_RECORD", "Urgency rules must define the routine band.")
    band = "routine"
    window_weeks = routine.get("window_weeks")
    urgency_terms = []
    for candidate in bands:
        matches = [
            term
            for term in candidate.get("trigger_terms", [])
            if term.lower() in lowered
        ]
        if matches:
            band = candidate.get("band")
            window_weeks = candidate.get("window_weeks")
            urgency_terms = matches
            break

    try:
        window_start = _parse_date(clock)
        window_end = window_start + timedelta(weeks=window_weeks)
    except (TypeError, ValueError):
        return failure("DATA_INVALID_RECORD", "Urgency rules or as_of date are invalid.")

    return success(
        {
            "hostile_input_detected": bool(hostile_matches),
            "hostile_matches": hostile_matches,
            "red_flags_detected": red_flags,
            "right_department": bool(department_terms),
            "department_terms_detected": department_terms,
            "mandatory_tests": protocol.get("mandatory_tests", []),
            "missing_tests": missing_tests,
            "band": band,
            "urgency_terms_detected": urgency_terms,
            "window_weeks": window_weeks,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        }
    )


def lookup_patient(patient_id: str) -> dict[str, Any]:
    """Return patient appointments and the directly joined contact record."""
    if not isinstance(patient_id, str) or not patient_id.strip():
        return failure("INVALID_PATIENT_ID", "patient_id must be a non-empty string.")
    try:
        patients = load_table("patients")
        contacts = load_table("contacts")
    except DataStoreError as exc:
        return _data_failure(exc)

    patient = next((p for p in patients if p.get("patient_id") == patient_id), None)
    if patient is None:
        return failure("PATIENT_NOT_FOUND", f"Patient {patient_id} does not exist.")
    contact = next((c for c in contacts if c.get("patient_id") == patient_id), None)
    return success({"patient": patient, "contact": contact})


def get_clinic_slots(
    specialty: str,
    band: str,
    window_start: str,
    window_end: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Return available slots inside a valid specialty/band booking window."""
    if not isinstance(specialty, str) or not specialty.strip():
        return failure("INVALID_SPECIALTY", "specialty must be a non-empty string.")
    if not isinstance(band, str) or not band.strip():
        return failure("INVALID_URGENCY_BAND", "band must be a non-empty string.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        return failure("INVALID_LIMIT", "limit must be an integer between 1 and 20.")

    try:
        specialties = load_table("specialties")
        bands = load_table("urgency_bands")
        slots = load_table("clinic_slots")
        clock = _parse_date(load_object("as_of").get("as_of"))
    except DataStoreError as exc:
        return _data_failure(exc)
    except (TypeError, ValueError):
        return failure("DATA_INVALID_RECORD", "as_of.json must contain a valid ISO date.")

    if not any(row.get("code") == specialty for row in specialties):
        return failure("SPECIALTY_NOT_FOUND", f"Specialty {specialty} does not exist.")
    urgency = next((row for row in bands if row.get("band") == band), None)
    if urgency is None:
        return failure("INVALID_URGENCY_BAND", f"Urgency band {band!r} is not valid.")

    try:
        start = _parse_date(window_start)
        end = _parse_date(window_end)
        legal_end = clock + timedelta(weeks=urgency["window_weeks"])
    except (KeyError, TypeError, ValueError):
        return failure("INVALID_DATE_WINDOW", "The booking window must contain ISO dates.")
    if start > end or start < clock or end > legal_end:
        return failure(
            "INVALID_DATE_WINDOW",
            f"Window must fall between {clock.isoformat()} and {legal_end.isoformat()}.",
        )

    available = sorted(
        (
            slot
            for slot in slots
            if slot.get("specialty") == specialty
            and slot.get("band") == band
            and start.isoformat() <= slot.get("date", "") <= end.isoformat()
            and slot.get("capacity_remaining", 0) > 0
        ),
        key=lambda slot: (slot["date"], slot["time"], slot["clinic"]),
    )[:limit]
    return success(
        {
            "result": "SLOTS_FOUND" if available else "NO_SLOT_WITHIN_WINDOW",
            "requested_window": {"start": window_start, "end": window_end},
            "slots": available,
        }
    )


def _parse_date(value: Any) -> date:
    if not isinstance(value, str):
        raise TypeError("date must be a string")
    return date.fromisoformat(value)


def _data_failure(exc: DataStoreError) -> dict[str, Any]:
    return failure(exc.code, exc.message)


READ_TOOLS = {
    "get_referral": get_referral,
    "get_system_date": get_system_date,
    "check_referral_criteria": check_referral_criteria,
    "lookup_patient": lookup_patient,
    "get_clinic_slots": get_clinic_slots,
}
