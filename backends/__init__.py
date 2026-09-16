"""Backend factory and shared response contract."""

from __future__ import annotations

from typing import Any, Protocol

from config import RunConfig


class Backend(Protocol):
    name: str
    model: str | None

    def next_move(self, transcript: list[dict[str, Any]]) -> dict[str, Any]: ...


def make_backend(
    case_id: str,
    config: RunConfig,
    system_prompt: str,
    backend: Backend | None = None,
) -> Backend:
    """Create one fresh backend instance for one run."""
    if backend is not None:
        return backend
    if config.backend == "scripted":
        from .scripted import ScriptedBackend

        return ScriptedBackend(case_id, call_mode=config.call_mode)
    if config.backend == "live":
        from .live import LiveBackend

        return LiveBackend(config, system_prompt)
    raise ValueError(f"Unsupported backend: {config.backend!r}.")


__all__ = ["Backend", "make_backend"]
