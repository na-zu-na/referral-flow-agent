"""Flask application exposing the existing Agent and evidence files."""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, request

from .readers import DataReadError, get_case, list_cases, read_audit_runs, read_evidence, read_tool_calls
from .run_manager import ConfirmationConflict, RunAlreadyActive, RunManager, RunNotFound
from dotenv import load_dotenv

load_dotenv()

def _ok(data: Any, status: int = 200):
    return jsonify({"ok": True, "data": data}), status


def _error(code: str, message: str, status: int):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


def _boolean(raw: str | None, name: str) -> bool | None:
    if raw is None:
        return None
    if raw.lower() not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false.")
    return raw.lower() == "true"


def create_app(*, manager: RunManager | None = None) -> Flask:
    app = Flask(__name__)
    runs = manager or RunManager()

    @app.errorhandler(DataReadError)
    def data_error(exc: DataReadError):
        return _error("RESULT_FILE_INVALID", str(exc), 500)

    @app.get("/api/health")
    def health():
        return _ok({"service": "referral-flow-agent-web-api", "status": "ready"})

    @app.get("/api/cases")
    def cases():
        tier = request.args.get("tier", "all")
        if tier not in {"core", "extended", "all"}:
            return _error("INVALID_TIER", "tier must be core, extended, or all.", 400)
        try:
            negative = _boolean(request.args.get("negative_case"), "negative_case")
        except ValueError as exc:
            return _error("INVALID_NEGATIVE_FILTER", str(exc), 400)
        items = list_cases(tier=tier, negative_case=negative)
        return _ok({"items": items, "count": len(items)})

    @app.get("/api/cases/<case_id>")
    def case_detail(case_id: str):
        item = get_case(case_id)
        return _ok(item) if item else _error("CASE_NOT_FOUND", f"Unknown case: {case_id}", 404)

    @app.post("/api/runs")
    def create_run():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("case_id"), str) or not body["case_id"].strip():
            return _error("INVALID_REQUEST", "case_id is required.", 400)
        case_id = body["case_id"].strip()
        if not get_case(case_id):
            return _error("CASE_NOT_FOUND", f"Unknown case: {case_id}", 404)
        values = {
            "backend": body.get("backend", "scripted"),
            "model": body.get("model"),
            "prompt_version": body.get("prompt_version", "v2"),
            "descriptor_version": body.get("descriptor_version", "v2"),
            "call_mode": body.get("execution_mode", "parallel"),
            "autonomy": body.get("autonomy", "confirm"),
            "temperature": body.get("temperature", 0.0),
        }
        if values["backend"] not in {"scripted", "live"}:
            return _error("INVALID_CONFIG", "backend must be scripted or live.", 400)
        if values["backend"] == "live" and not values["model"]:
            return _error("MODEL_REQUIRED", "A live run requires an exact model ID.", 400)
        if values["backend"] == "live" and not os.getenv("OPENROUTER_API_KEY"):
            return _error("API_KEY_MISSING", "The server has no live-backend API key configured.", 503)
        if values["prompt_version"] not in {"v1", "v2"} or values["descriptor_version"] not in {"v1", "v2"}:
            return _error("INVALID_CONFIG", "prompt_version and descriptor_version must be v1 or v2.", 400)
        if values["call_mode"] not in {"parallel", "sequential"} or values["autonomy"] not in {"suggest", "confirm", "act"}:
            return _error("INVALID_CONFIG", "Invalid execution_mode or autonomy.", 400)
        temperature = values["temperature"]
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or temperature < 0:
            return _error("INVALID_CONFIG", "temperature must be a non-negative number.", 400)
        try:
            return _ok(runs.start(case_id, values), 202)
        except RunAlreadyActive:
            return _error("RUN_ALREADY_ACTIVE", "Another run is still active.", 409)

    @app.get("/api/runs/<job_id>")
    def get_run(job_id: str):
        try:
            return _ok(runs.get(job_id))
        except RunNotFound:
            return _error("RUN_NOT_FOUND", f"Unknown run: {job_id}", 404)

    @app.post("/api/runs/<job_id>/confirmation")
    def confirm_run(job_id: str):
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("approved"), bool):
            return _error("INVALID_CONFIRMATION", "approved must be a boolean.", 400)
        try:
            return _ok(runs.confirm(job_id, body["approved"]))
        except RunNotFound:
            return _error("RUN_NOT_FOUND", f"Unknown run: {job_id}", 404)
        except ConfirmationConflict as exc:
            return _error(str(exc), "This run is not awaiting an unresolved confirmation.", 409)

    @app.get("/api/evidence")
    def evidence():
        return _ok(read_evidence())

    @app.get("/api/audit/runs")
    def audit_runs():
        try:
            passed = _boolean(request.args.get("passed"), "passed")
            negative = _boolean(request.args.get("negative_case"), "negative_case")
            limit = int(request.args.get("limit", "100"))
            if not 1 <= limit <= 500:
                raise ValueError("limit must be between 1 and 500.")
        except ValueError as exc:
            return _error("INVALID_FILTER", str(exc), 400)
        items = read_audit_runs(
            case_id=request.args.get("case_id"), model=request.args.get("model"),
            passed=passed, negative_case=negative, limit=limit,
        )
        return _ok({"items": items, "count": len(items)})

    @app.get("/api/audit/tool-calls")
    def audit_tool_calls():
        run_id = request.args.get("run_id", "").strip()
        if not run_id:
            return _error("RUN_ID_REQUIRED", "run_id is required.", 400)
        items = read_tool_calls(run_id)
        if items is None:
            return _error("AUDIT_RUN_NOT_FOUND", f"Unknown audit run: {run_id}", 404)
        return _ok({"run_id": run_id, "items": items, "count": len(items)})

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.getenv("WEB_PORT", "5000")), debug=False)
