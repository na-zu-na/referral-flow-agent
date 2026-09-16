"""Vendor-neutral configuration for the referral Agent.

The rest of the repository reads :class:`RunConfig`; only the live backend
knows the OpenRouter wire format.  Scripted mode is deliberately the default.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, replace
from typing import Any


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw in (None, "") else int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw in (None, "") else float(raw)


@dataclass(frozen=True, slots=True)
class RunConfig:
    """All settings needed for one isolated Agent run."""

    backend: str = "scripted"
    model: str | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    descriptor_version: str = "v2"
    call_mode: str = "parallel"
    autonomy: str = "confirm"
    max_turns: int = 8
    max_tokens: int = 60_000
    implementation_iteration_cap: int = 12
    temperature: float = 0.0
    request_timeout_seconds: int = 90
    price_input_per_million: float = 0.0
    price_output_per_million: float = 0.0

    def __post_init__(self) -> None:
        if self.backend not in {"scripted", "live"}:
            raise ValueError("backend must be 'scripted' or 'live'.")
        if self.backend == "live" and not self.model:
            raise ValueError("A live run requires a model name.")
        if self.descriptor_version not in {"v1", "v2"}:
            raise ValueError("descriptor_version must be 'v1' or 'v2'.")
        if self.call_mode not in {"sequential", "parallel"}:
            raise ValueError("call_mode must be 'sequential' or 'parallel'.")
        if self.autonomy not in {"suggest", "confirm", "act"}:
            raise ValueError("autonomy must be 'suggest', 'confirm', or 'act'.")
        for name in ("max_turns", "max_tokens", "implementation_iteration_cap"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        if self.implementation_iteration_cap < self.max_turns + 1:
            raise ValueError("implementation_iteration_cap must allow a final move.")
        if self.temperature < 0:
            raise ValueError("temperature must be non-negative.")
        if self.price_input_per_million < 0 or self.price_output_per_million < 0:
            raise ValueError("Token prices must be non-negative.")

    @classmethod
    def from_env(cls, **overrides: Any) -> "RunConfig":
        """Load configuration without placing secrets in source control."""
        backend = os.getenv("A2_BACKEND", "scripted")
        model = os.getenv("A2_MODEL") or ("openai/gpt-4o-mini" if backend == "live" else None)
        config = cls(
            backend=backend,
            model=model,
            base_url=os.getenv("A2_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            descriptor_version=os.getenv("A2_DESCRIPTOR_VERSION", "v2"),
            call_mode=os.getenv("A2_CALL_MODE", "parallel"),
            autonomy=os.getenv("A2_AUTONOMY", "confirm"),
            max_turns=_env_int("A2_MAX_TURNS", 8),
            max_tokens=_env_int("A2_MAX_TOKENS", 60_000),
            implementation_iteration_cap=_env_int("A2_ITERATION_CAP", 12),
            temperature=_env_float("A2_TEMPERATURE", 0.0),
            request_timeout_seconds=_env_int("A2_REQUEST_TIMEOUT", 90),
            price_input_per_million=_env_float("A2_PRICE_INPUT", 0.0),
            price_output_per_million=_env_float("A2_PRICE_OUTPUT", 0.0),
        )
        return replace(config, **overrides) if overrides else config

    def public_dict(self) -> dict[str, Any]:
        """Return auditable settings with the API secret removed."""
        value = asdict(self)
        value.pop("api_key", None)
        return value

    def summary(self) -> str:
        model = self.model or "(none: deterministic scripted backend)"
        return (
            f"backend={self.backend} model={model} descriptors={self.descriptor_version} "
            f"call_mode={self.call_mode} autonomy={self.autonomy} max_turns={self.max_turns} "
            f"max_tokens={self.max_tokens}"
        )


DEFAULT_CONFIG = RunConfig.from_env()

__all__ = ["DEFAULT_CONFIG", "RunConfig"]
