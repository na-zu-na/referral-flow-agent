"""Canonical field names and measurement vocabulary."""
from typing import Literal, TypedDict

MeasurementStatus = Literal[
    "MEASURED", "PROVIDER_REPORTED", "RECOMPUTED", "ESTIMATED",
    "ASSUMED", "NOT_MEASURED", "UNKNOWN",
]


class NormalizedRun(TypedDict, total=False):
    experiment_id: str
    run_id: str
    case_id: str
    trial: int
    model: str
    prompt_version: str
    descriptor_version: str
    status: str
    passed: bool
    actual_decision: str | None
    input_tokens: int | None
    output_tokens: int | None
    provider_cost_usd: float | None
    provider_cost_measurement_status: MeasurementStatus

