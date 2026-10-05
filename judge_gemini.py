"""Gemini backend for HingeAuto judging.

Uses the AI Studio free tier (`GEMINI_API_KEY` in `.env`) - fast (~2s),
vision-native, and honors forced function calls, so the same
`submit_decision` contract as the other backends holds.

Set in config.py:
  JUDGE_BACKEND = "gemini"
  GEMINI_MODEL  = "gemini-3.5-flash-lite"   # or "gemini-3.8-flash"
"""

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
        from google import genai
    except ImportError as e:
        raise RuntimeError(
            "The `google-genai` package isn't installed. Run "
            "`pip install google-genai`."
        ) from e
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get(
        "GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set. "
            "Add it to .env - see .env.example."
        )
    return genai.Client(api_key=api_key)


def judge(frames: list[bytes]) -> Decision:
    """Given an ordered list of PNG frames of one profile, return a Decision."""
    from google.genai import types

    client = _client()
    model = getattr(config, "GEMINI_MODEL", "gemini-3.5-flash-lite")

    parts = [
        types.Part.from_bytes(data=f, mime_type="image/png")
        for f in frames
    ]
    parts.append(types.Part.from_text(text=(
        packed_caption(len(frames), len(frames), "one Hinge profile")
        + " Decide whether to like or skip."
    )))

    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(),
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="submit_decision",
                    description=(
                        "Submit a like/skip decision for this Hinge profile."
                    ),
                    parameters=DECIDE_INPUT_SCHEMA,
                )
            ])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY",
                    allowed_function_names=["submit_decision"],
                )
            ),
            temperature=0.2,
            max_output_tokens=1000,
        ),
    )

    usage = {"input_tokens": 0, "output_tokens": 0,
             "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    meta = getattr(response, "usage_metadata", None)
    if meta is not None:
        usage["input_tokens"] = getattr(meta, "prompt_token_count", 0) or 0
        usage["output_tokens"] = (
            getattr(meta, "candidates_token_count", 0) or 0)

    candidates = getattr(response, "candidates", None) or []
    content = getattr(candidates[0], "content", None) if candidates else None
    for part in getattr(content, "parts", None) or []:
        call = getattr(part, "function_call", None)
        if call is None or getattr(call, "name", "") != "submit_decision":
            continue
        args = getattr(call, "args", {}) or {}
        decision = _decision_from_args(dict(args), usage)
        enforce_premade_verbatim(decision)
        return decision

    raise RuntimeError(
        f"Gemini ({model}) did not return a submit_decision call. "
        f"finish_reason={getattr(candidates[0], 'finish_reason', '?') if candidates else '?'}"
    )
