"""Public tool-layer API."""

from .registry import (
    DESCRIPTORS,
    DESCRIPTORS_V1,
    DESCRIPTORS_V2,
    REGISTRY,
    call_tool,
    failure,
    get_descriptors,
    register_tool,
    success,
)
from .referral_tools import (
    READ_TOOLS,
    check_referral_criteria,
    get_clinic_slots,
    get_referral,
    get_system_date,
    lookup_patient,
)
from .booking import book_slot

TOOLS = {**READ_TOOLS, "book_slot": book_slot}

for _name, _function in TOOLS.items():
    if _name not in REGISTRY:
        register_tool(_name, _function)

__all__ = [
    "DESCRIPTORS",
    "DESCRIPTORS_V1",
    "DESCRIPTORS_V2",
    "REGISTRY",
    "READ_TOOLS",
    "TOOLS",
    "book_slot",
    "call_tool",
    "check_referral_criteria",
    "failure",
    "get_clinic_slots",
    "get_descriptors",
    "get_referral",
    "get_system_date",
    "lookup_patient",
    "register_tool",
    "success",
]
