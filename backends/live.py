"""OpenRouter adapter. This is the only module aware of vendor wire format."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from agent.schemas import BackendError, InvalidModelOutput, parse_json_move
from config import RunConfig


class LiveBackend:
    name = "live"

    def __init__(self, config: RunConfig, system_prompt: str):
        if not config.api_key:
            raise BackendError(
                "OPENROUTER_API_KEY is required for live mode; scripted mode needs no key."
            )
        self.config = config
        self.model = config.model
        self.system_prompt = system_prompt

    def next_move(self, transcript: list[dict[str, Any]]) -> dict[str, Any]:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(_vendor_messages(transcript))
        payload = _post_openrouter(self.config, messages)
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError("Live provider response did not contain message content.") from exc
        usage = payload.get("usage") or {}
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
        measured = all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in (input_tokens, output_tokens)
        ) and bool(usage)
        cached_input_tokens = _usage_token_detail(
            usage,
            "cached_input_tokens",
            ("prompt_tokens_details", "cached_tokens"),
            ("input_tokens_details", "cached_tokens"),
        )
        reasoning_tokens = _usage_token_detail(
            usage,
            "reasoning_tokens",
            ("completion_tokens_details", "reasoning_tokens"),
            ("output_tokens_details", "reasoning_tokens"),
        )
        normalized_usage = {
            "input_tokens": input_tokens if measured else 0,
            "output_tokens": output_tokens if measured else 0,
            "measured": measured,
            "provider_cost_usd": _nonnegative_number(usage.get("cost")),
        }
        if cached_input_tokens is not None:
            normalized_usage["cached_input_tokens"] = cached_input_tokens
        if reasoning_tokens is not None:
            normalized_usage["reasoning_tokens"] = reasoning_tokens
        try:
            move = parse_json_move(content)
        except InvalidModelOutput as exc:
            exc.usage = normalized_usage
            raise
        return {
            "move": move,
            "usage": normalized_usage,
        }


def _vendor_messages(transcript: list[dict[str, Any]]) -> list[dict[str, str]]:
    converted = []
    for item in transcript:
        role = item.get("role")
        if role not in {"user", "assistant"}:
            raise BackendError("Transcript contains an unsupported role.")
        content = item.get("content")
        converted.append(
            {
                "role": role,
                "content": content if isinstance(content, str) else json.dumps(content, sort_keys=True),
            }
        )
    return converted


def _post_openrouter(config: RunConfig, messages: list[dict[str, str]]) -> dict[str, Any]:
    """The one provider-specific request function in the repository."""
    body = json.dumps(
        {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        config.base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + config.api_key,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost/pe6201-a2",
            "X-Title": "PE6201 A2 Referral Agent",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise BackendError(f"Live provider returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BackendError(f"Live provider request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise BackendError("Live provider returned a non-object response.")
    return payload


def _nonnegative_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return float(value)
    return None


def _usage_token_detail(
    usage: dict[str, Any], direct_name: str, *nested_paths: tuple[str, str]
) -> int | None:
    value = usage.get(direct_name)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    for container_name, field_name in nested_paths:
        container = usage.get(container_name)
        value = container.get(field_name) if isinstance(container, dict) else None
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return None
