"""Generic OpenAI-compatible cloud backend for HingeAuto judging.

This is the "bring your own cloud key" slot: any provider speaking the
OpenAI chat-completions dialect works by setting two knobs -

Set in config.py:
  JUDGE_BACKEND = "openai"
  OPENAI_BASE_URL = "https://api.openai.com/v1"   # or Groq, OpenRouter, ...
  OPENAI_MODEL    = "gpt-4o-mini"                 # provider's model id

Set in your .env (or shell):
  OPENAI_API_KEY=...   # the key for whichever provider BASE_URL points at

Known-good combinations:
  - OpenAI gpt-4o / gpt-4o-mini: vision + tools, the reference target.
  - Groq (https://api.groq.com/openai/v1): fast, but keys we tested
    expose TEXT-ONLY models - the tool envelope below is validated, the
    image path is not. Do not run the loop on a vision-less model.
  - abliteration.ai /v1/chat/completions: 4-image cap; use pack_frames.

Validation status: text+forced-tool path smoke-tested (Groq). Image path
assumes a vision-capable model - run your own judge smoke test (synthetic
frames, then one real screenshot) before going live.
"""

import base64
import json
import os

import config
from judge_common import (
    DECIDE_INPUT_SCHEMA,
    Decision,
    build_system_prompt,
    enforce_premade_verbatim,
    packed_caption,
)
from judge_ollama import _decision_from_args


def _client():
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError(
            "The `openai` package isn't installed. Run "
            "`pip install openai`."
        ) from e
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env - see .env.example."
        )
    base_url = getattr(config, "OPENAI_BASE_URL", None) or os.environ.get(
        "OPENAI_BASE_URL", "https://api.openai.com/v1"
    )
    return OpenAI(api_key=api_key, base_url=base_url)


def _image_part(png: bytes) -> dict:
    return {
        "type": "image_url",
        "image_url": {
            "url": "data:image/png;base64,"
            + base64.standard_b64encode(png).decode("utf-8"),
        },
    }


def judge(frames: list[bytes]) -> Decision:
    """Given an ordered list of PNG frames of one profile, return a Decision."""
    client = _client()
    model = getattr(config, "OPENAI_MODEL", "gpt-4o-mini")

    content = [_image_part(f) for f in frames]
    content.append({
        "type": "text",
        "text": packed_caption(len(frames), len(frames), "one Hinge profile")
        + " Decide whether to like or skip.",
    })

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": content},
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": "submit_decision",
                "description": (
                    "Submit a like/skip decision for this Hinge profile."
                ),
                "parameters": DECIDE_INPUT_SCHEMA,
            },
        }],
        tool_choice={
            "type": "function",
            "function": {"name": "submit_decision"},
        },
        temperature=0.2,
        max_tokens=1000,
    )

    usage = {"input_tokens": 0, "output_tokens": 0,
             "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    u = getattr(response, "usage", None)
    if u is not None:
        usage["input_tokens"] = getattr(u, "prompt_tokens", 0) or 0
        usage["output_tokens"] = getattr(u, "completion_tokens", 0) or 0

    choices = getattr(response, "choices", None) or []
    message = getattr(choices[0], "message", None) if choices else None
    for call in getattr(message, "tool_calls", None) or []:
        fn = getattr(call, "function", None)
        if fn is None or getattr(fn, "name", "") != "submit_decision":
            continue
        raw = getattr(fn, "arguments", "") or "{}"
        try:
            args = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (json.JSONDecodeError, ValueError):
            args = {}
        decision = _decision_from_args(args, usage)
        enforce_premade_verbatim(decision)
        return decision

    raise RuntimeError(
        f"OpenAI-compatible ({model}) did not return a submit_decision call. "
        f"finish_reason={getattr(choices[0], 'finish_reason', '?') if choices else '?'}"
    )
