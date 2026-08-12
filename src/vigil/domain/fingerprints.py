"""Request fingerprints used by circuit-breaker controls."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def request_fingerprint(*, model: str, messages: list[dict[str, Any]] | None) -> str:
    """Hash normalized model + messages for equivalent-request detection.

    Bodies are never retained — only the digest is used in decisions and audit.
    """
    normalized_messages = _normalize_messages(messages or [])
    payload = {
        "model": model.strip(),
        "messages": normalized_messages,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip()
        content = message.get("content")
        if isinstance(content, str):
            content_value: Any = content.strip()
        else:
            content_value = content
        entry: dict[str, Any] = {"role": role, "content": content_value}
        if "name" in message:
            entry["name"] = message["name"]
        if "tool_calls" in message:
            entry["tool_calls"] = message["tool_calls"]
        normalized.append(entry)
    return normalized
