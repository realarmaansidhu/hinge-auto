"""Per-profile structured logging for the autopilot loop.

Each profile run produces one JSONL line in `debug/session_log.jsonl`
with timing, token usage, decision, and message metadata. Append-only
and machine-parseable so chart-making downstream is trivial.
"""

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import config


# Reference per-1M-token prices (USD) by cloud route. Free routes (local
# Ollama, Gemini AI Studio free tier) are handled in estimated_cost, not
# here. Prices drift - update when providers adjust.
PRICE_PER_MTOK_BY_BACKEND = {
    # Anthropic Sonnet reference (the "anthropic" route default).
    "anthropic": {
        "input_tokens":                3.00,
        "output_tokens":              15.00,
        "cache_creation_input_tokens": 3.75,
        "cache_read_input_tokens":     0.30,
    },
    # OpenAI gpt-4o-mini reference (the "openai" route default). Swap in
    # your provider's numbers when using Groq/OpenRouter/etc.
    "openai": {
        "input_tokens":                0.15,
        "output_tokens":               0.60,
        "cache_creation_input_tokens": 0.00,
        "cache_read_input_tokens":     0.075,
    },
}


def estimated_cost(usage: dict[str, int]) -> float:
    """Dollar estimate from a usage dict returned by judge()."""
    backend = getattr(config, "JUDGE_BACKEND", "")
    # Free routes: local Ollama (no Cloud key) and Gemini on the AI Studio
    # free tier. (If you attach billing to the Gemini project, add a
    # "gemini" entry to PRICE_PER_MTOK_BY_BACKEND instead.)
    if backend == "gemini":
        return 0.0
    if backend == "ollama" and not os.environ.get("OLLAMA_API_KEY"):
        return 0.0
    prices = PRICE_PER_MTOK_BY_BACKEND.get(backend,
                                           PRICE_PER_MTOK_BY_BACKEND["anthropic"])
    return sum(
        usage.get(k, 0) * price / 1_000_000
        for k, price in prices.items()
    )


def log_profile(
    profile_idx: int,
    decision,
    timing: dict[str, float],
    log_path: Path | None = None,
) -> None:
    """Append a JSONL record for one profile."""
    if log_path is None:
        log_path = config.DEBUG_DIR / "session_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "profile_idx": profile_idx,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": config.MODE_NAME,
        "name": decision.name,
        "decision": decision.decision,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning,
        "message": decision.message,
        "message_length": len(decision.message),
        "message_archetype": decision.message_archetype,
        "premade_id": decision.premade_id,
        "prompt_referenced": decision.prompt_referenced,
        "skip_reason": decision.skip_reason,
        "timing": timing,
        "tokens": decision.usage,
        "estimated_cost_usd": round(estimated_cost(decision.usage), 5),
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_running_totals(
    profiles_seen: int,
    likes_sent: int,
    skips: int,
    total_cost: float,
    total_seconds: float,
) -> None:
    """One-line summary printed every loop iteration."""
    avg_cost = total_cost / profiles_seen if profiles_seen else 0
    avg_time = total_seconds / profiles_seen if profiles_seen else 0
    like_rate = likes_sent / profiles_seen if profiles_seen else 0
    print(
        f"[totals] {profiles_seen} profiles | {likes_sent} likes "
        f"({like_rate:.0%}) | {skips} skips | "
        f"${total_cost:.3f} (~${avg_cost:.4f}/profile) | "
        f"avg {avg_time:.1f}s/profile"
    )
