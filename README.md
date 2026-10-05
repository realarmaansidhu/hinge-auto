# hinge-auto

Drive Hinge from your laptop: an Android emulator runs the app, this repo
drives it over ADB. For each profile it captures a scroll of screenshots,
a vision model judges them against your rubric, and the loop either skips
or taps like with a generated opener.

This is a fork of houseunlimited/hinge-auto. The fork adds a pluggable
judge backend (local Ollama plus cloud: Gemini, Anthropic,
OpenAI-compatible), a heart-button detector that works with Hinge's
current UI, and hardening for the message-typing path. Details below.

> Warning: this violates Hinge's Terms of Service. Accounts get banned
> without appeal, and Hinge can fingerprint emulators. Use a throwaway
> account or do not run it at all. This fork is kept as reference; the
> live loop is archived, not operated.

## How it works

`main.py` runs the loop: capture 7 frames of the current profile, call
`judge(frames)`, then tap skip or like-with-message. Decisions are forced
through a `submit_decision` tool call so the model always returns a
structured `Decision` (like/skip, reasoning, opener, analytics labels).

- `judge_common.py` - shared system prompt, tool schema, `Decision`
  dataclass, voice/premade/age-gate assembly, frame packing, message
  sanitizer.
- `judge.py` / `judge_gemini.py` / `judge_openai.py` / `judge_ollama.py` -
  one module per backend, same `judge(frames)` contract.
- `vision.py` - finds UI elements whose position shifts per profile
  (photo hearts, Send Like button) with blob detection.
- `modes/` - rubric files (`PREFERENCES`, age band, voice, premade
  openers, like caps). `voice/` - opener style templates.
- `adb.py` - thin ADB wrapper. `metrics.py` - JSONL session logging.
- `scan_self.py` - reviews your own profile (no swiping involved).
  `matches_scan.py` - Matches-tab analytics.

## Requirements

- Python 3.10+
- `adb` on PATH (Android platform tools)
- Android emulator at 1080x2424 (Pixel 10 profile is the calibrated
  default; other screens need `config.COORDS` recalibrated)
- One of: local Ollama with a vision model, or an API key (Gemini,
  Anthropic, or OpenAI-compatible)

## Setup

1. Create the env and install deps:

       python3 -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt
       pip install -r requirements-ollama.txt   # only for the local route

2. Copy `.env.example` to `.env` and fill in the key for your backend.
   Never commit `.env`.

3. Start the emulator, install Hinge, sign in with a throwaway account,
   and leave it on the Discover tab. `adb devices` must show exactly
   one device (unplug physical phones; bare `adb` commands fail with
   two attached).

4. Calibrate: `python calibrate.py`, open `calibrate.png` in a viewer
   that shows cursor coordinates, and update any `config.COORDS` values
   that do not match your screen.

5. Write a mode: copy `modes/example_lenient.py` (or `example_strict.py`)
   to `modes/mine.py`, edit `PREFERENCES` in your own words, optionally
   set `MESSAGE_VOICE`, and point `ACTIVE_MODE` in `config.py` at it.

6. Run: `python main.py` (Ctrl-C stops it). Review decisions in
   `debug/session_log.jsonl` and the `debug/liked|skipped/` folders,
   then iterate on your rubric.

## Judge backends

Pick with `JUDGE_BACKEND` in `config.py`. The loop is backend-agnostic;
only judgment quality, speed, and cost change.

| Backend | Key | Default model | Speed | Cost |
|---|---|---|---|---|
| `ollama` (local) | none (`ollama serve` + pulled model) | `qwen3-vl:8b-instruct` | ~7 min/profile | $0 |
| `gemini` (default) | `GEMINI_API_KEY` (AI Studio free tier) | `gemini-3.5-flash-lite` | ~2 s/judge | $0 |
| `anthropic` | `ANTHROPIC_API_KEY` (+ optional `ANTHROPIC_BASE_URL`) | `claude-sonnet-4-6` | seconds | ~$0.02-0.05/profile |
| `openai` | `OPENAI_API_KEY` + `OPENAI_BASE_URL` | `gpt-4o-mini` | seconds | provider pricing |

Notes from testing each route:

- Local Ollama needs `OLLAMA_NUM_CTX = 32768` in config: 7 full-res
  screenshots overflow the 4K default context. Use the `-instruct`
  tag, not the thinking variant (its 3K-token traces make each
  judgment take minutes).
- The `openai` slot fits OpenAI, Groq, OpenRouter, and similar
  endpoints. The model must be vision-capable with tool support.
  Groq keys we tried exposed text-only models, so always smoke-test
  (`judge` on synthetic frames, then one real screenshot) before live.
- We tried abliteration.ai's Anthropic-compatible surface and dropped
  it: 4-image request cap, 413s on tall stitched frames, and its
  gateway intermittently ignores forced tool calls. Its OpenAI
  surface behaved better, but we do not recommend it.
- `pack_frames` (in `judge_common`) stitches captures for
  image-capped providers. Local Ollama and Gemini take all 7 raw.

## What this fork changed vs upstream

- New `judge_gemini.py` and `judge_openai.py` backends; `JUDGE_BACKEND`
  now dispatches `ollama` (local) vs `gemini` / `anthropic` / `openai`
  (cloud). Backend-aware cost estimates in `metrics.py`.
- `vision.find_first_heart` handles Hinge's black-circle heart buttons
  (the old white-only detector never fired on current builds) plus a
  white-glyph fallback for buttons sitting on dark photos.
- `sanitize_message` + chunked `adb input text`: small models emit
  smart quotes and long single-burst typing drops characters; both
  broke real sends.
- Drift clamps for small-model tool output (`skip_reason`, archetype
  enums), corrected pixel-gain check after typing, dead-config notes.
- Personal `modes/mine.py` example (lenient + polished voice, cap 5).

## Costs (measured, Oct 2026)

- Local Ollama: $0. ~20s capture + ~7 min judge + ~1 min act per profile.
- Gemini free tier: $0. ~2 s per judgment, full loop under 2 min/profile.
- Anthropic Sonnet: ~$0.02-0.05/profile at list pricing.

## Troubleshooting

- `more than one device/emulator`: unplug the phone or
  `export ANDROID_SERIAL=emulator-5554`.
- Judge fails 3x in a row: the loop skips the profile; auth/billing
  errors halt it instead of burning swipes blind.
- Likes never fire: run the heart detector against a screenshot
  (`vision.find_first_heart`) - Hinge changes button styling between
  builds.
- Typed text looks cut off: check the WARN line - chunked typing plus
  the density check usually catches it; host CPU contention is the
  common cause.
- `compose_close` in config is unused (leftover): the loop never needs
  to close compose without sending.

## License

MIT, inherited from upstream.
