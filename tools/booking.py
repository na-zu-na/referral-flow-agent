"""Simulated booking tool; all mutations live inside one GuardrailState."""

from __future__ import annotations

from typing import Any

from guardrails import GuardrailState, authorize_booking

from .data_store import DataStoreError, load_table
from .registry import failure, success


def book_slot(
    referral_id: str,
    clinic: str,
    specialty: str,
    band: str,
    date: str,
    time: str,
    *,
    _state: GuardrailState,
    _call_id: str,
) -> dict[str, Any]:
    """Authorize and commit one booking to per-run memory."""
    arguments = {
        "referral_id": referral_id,
        "clinic": clinic,
        "specialty": specialty,
        "band": band,
        "date": date,
        "time": time,
    }
    authorize_booking(
        {"id": _call_id, "name": "book_slot", "arguments": arguments},
        _state,
    )

    try:
        referrals = load_table("referrals")
        slots = load_table("clinic_slots")
    except DataStoreError as exc:
        return failure(exc.code, exc.message)

    referral = next((row for row in referrals if row.get("referral_id") == referral_id), None)
    if referral is None:
        return failure("REFERRAL_NOT_FOUND", f"Referral {referral_id} does not exist.")
    if referral.get("specialty") != specialty:
        return failure("SPECIALTY_MISMATCH", "Booking specialty differs from the referral.")
    if any(booking.get("referral_id") == referral_id for booking in _state.bookings):
        return failure("DUPLICATE_BOOKING", f"Referral {referral_id} is already booked.")

    requested = {key: arguments[key] for key in ("clinic", "specialty", "band", "date", "time")}
    slot = next(
        (
            row
            for row in slots
            if all(row.get(key) == value for key, value in requested.items())
        ),
        None,
    )
    if slot is None:
        return failure("SLOT_NOT_FOUND", "The requested clinic slot does not exist.")

    key = _slot_key(requested)
    used = _state.slot_capacity_used.get(key, 0)
    capacity = slot.get("capacity_remaining", 0)
    if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity - used <= 0:
        return failure("SLOT_FULL", "The requested clinic slot has no remaining capacity.")

    booking = {
        "booked": True,
        "referral_id": referral_id,
        **requested,
        "capacity_remaining_after": capacity - used - 1,
    }
    _state.slot_capacity_used[key] = used + 1
    _state.bookings.append(booking)
    return success(booking)


def _slot_key(values: dict[str, Any]) -> str:
    return "|".join(
        str(values[key]) for key in ("clinic", "specialty", "band", "date", "time")
    )
