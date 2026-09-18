"""In-memory execution manager for one interactive Agent run at a time."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import threading
from typing import Any, Callable
from uuid import uuid4

from agent import run_case
from config import RunConfig
from evaluation.harness import score_record

from .readers import get_case_and_answer


class RunAlreadyActive(RuntimeError):
    pass


class RunNotFound(KeyError):
    pass


class ConfirmationConflict(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RunManager:
    """A small process-local job registry; restart intentionally clears it."""

    def __init__(self, *, confirmation_timeout: float = 300.0) -> None:
        self.confirmation_timeout = confirmation_timeout
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start(self, case_id: str, overrides: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if any(not job["finished"] for job in self._jobs.values()):
                raise RunAlreadyActive
            job_id = str(uuid4())
            job = {
                "job_id": job_id, "case_id": case_id, "status": "queued",
                "created_at": _now(), "updated_at": _now(), "confirmation": None,
                "expected": None, "evaluation": None, "record": None,
                "error": None, "finished": False, "decision": None,
                "decision_event": threading.Event(),
            }
            self._jobs[job_id] = job
        threading.Thread(target=self._run, args=(job_id, overrides), daemon=True).start()
        return {"job_id": job_id, "status": "queued", "case_id": case_id}

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise RunNotFound(job_id)
            return deepcopy({key: value for key, value in job.items() if key not in {"decision", "decision_event"}})

    def confirm(self, job_id: str, approved: bool) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise RunNotFound(job_id)
            if job["decision"] is not None:
                raise ConfirmationConflict("CONFIRMATION_ALREADY_SUBMITTED")
            if job["status"] != "confirmation_required":
                raise ConfirmationConflict("CONFIRMATION_NOT_REQUIRED")
            job["decision"] = approved
            job["status"] = "running"
            job["updated_at"] = _now()
            job["decision_event"].set()
        return {"job_id": job_id, "approved": approved, "status": "running"}

    def _approve(self, job_id: str, confirmation: dict[str, Any]) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            job["confirmation"] = confirmation
            job["status"] = "confirmation_required"
            job["updated_at"] = _now()
            event = job["decision_event"]
        if not event.wait(self.confirmation_timeout):
            return False
        with self._lock:
            return bool(self._jobs[job_id]["decision"])

    def _run(self, job_id: str, overrides: dict[str, Any]) -> None:
        try:
            with self._lock:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["updated_at"] = _now()
                case_id = self._jobs[job_id]["case_id"]
            config = RunConfig.from_env(**overrides)
            record = run_case(case_id, config=config, approve=lambda item: self._approve(job_id, item))
            pair = get_case_and_answer(case_id)
            if pair is None:
                raise ValueError(f"Case disappeared during run: {case_id}")
            case, answer = pair
            scored = score_record(case, answer, record, 1)
            public_record = {key: value for key, value in record.items() if key not in {"transcript", "moves"}}
            evaluation = {
                "passed": scored.get("passed"),
                "failure_reason": "; ".join(scored.get("failures") or []),
            }
            with self._lock:
                job = self._jobs[job_id]
                job["record"] = public_record
                job["expected"] = {"decision": answer.get("expected_decision")}
                job["evaluation"] = evaluation
                if record.get("status") == "confirmation_required":
                    job["status"] = "confirmation_rejected" if job["decision"] is False else "failed"
                    if job["decision"] is None:
                        job["error"] = {"type": "ConfirmationTimeout", "message": "Confirmation timed out."}
                else:
                    job["status"] = record.get("status") or "completed"
                job["finished"] = True
                job["updated_at"] = _now()
        except Exception as exc:  # The worker must always produce a pollable terminal state.
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "failed"
                job["error"] = {"type": type(exc).__name__, "message": str(exc)}
                job["finished"] = True
                job["updated_at"] = _now()
