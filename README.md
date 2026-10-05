# hinge-auto

Drive Hinge from your laptop: an Android emulator runs the app, this repo
drives it over ADB. For each profile it captures a scroll of screenshots,
a vision model judges them against your rubric, and the loop either skips
or taps like with a generated opener.

This is a fork of houseunlimited/hinge-auto. The fork adds a pluggable
judge backend (local Ollama plus cloud: Gemini, Anthropic,
OpenAI-compatible), a heart-button detector that works with Hinge's
current UI, and hardening for the message-typing path. The changelog is
at the bottom.

> Warning: this violates Hinge's Terms of Service. Accounts get banned
> without appeal, and Hinge can fingerprint emulators. Use a throwaway
> account or do not run it at all.

## Contents

1. [What you need](#1-what-you-need)
2. [Clone and Python setup](#2-clone-and-python-setup)
3. [Install ADB](#3-install-adb)
4. [Android Studio and the Pixel 10 emulator](#4-android-studio-and-the-pixel-10-emulator)
5. [Install Hinge on the emulator](#5-install-hinge-on-the-emulator)
6. [Pick a judge backend](#6-pick-a-judge-backend)
7. [Calibrate tap coordinates](#7-calibrate-tap-coordinates)
8. [Write your mode (rubric)](#8-write-your-mode-rubric)
9. [Optional: check your own profile first](#9-optional-check-your-own-profile-first)
10. [First live run](#10-first-live-run)
11. [Costs (measured)](#11-costs-measured)
12. [How it works under the hood](#12-how-it-works-under-the-hood)
13. [Troubleshooting](#13-troubleshooting)
14. [Fork changelog vs upstream](#14-fork-changelog-vs-upstream)
15. [License](#15-license)

## 1. What you need

- A computer: macOS or Windows, 8 GB RAM minimum (16 GB if you want
  the local Ollama route below).
- A Google account (for the emulator's Play Store, optional) and a
  **throwaway Hinge account**. Do not use your main Hinge account.
- One of these for the AI judge:
  - a free Google AI Studio key (recommended: fast and $0), or
  - an Anthropic or OpenAI-compatible key, or
  - local Ollama (no key, no cloud, slower).
- About an hour the first time: emulator download, Hinge setup,
  calibration, and writing your rubric.

## 2. Clone and Python setup

You need Python 3.10 or newer. Check with:

    python3 --version

Clone the repo and set up an isolated environment (keeps dependencies
off your system Python):

    git clone https://github.com/realarmaansidhu/hinge-auto.git
    cd hinge-auto
    python3 -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

If you chose the local Ollama route, also install its client:

    pip install -r requirements-ollama.txt

Use `source .venv/bin/activate` in every new terminal before running
anything here.

## 3. Install ADB

ADB (Android Debug Bridge) is the command line the scripts use to tap
and screenshot the emulator. Install it, then confirm:

    adb version

- macOS: `brew install --cask android-platform-tools`
- Windows: install Android Studio (step 4) and add its
  `platform-tools` folder to PATH, or download platform-tools
  standalone from Google.

## 4. Android Studio and the Pixel 10 emulator

1. Install Android Studio from Google (developer.android.com/studio)
   and open it once. The first-run wizard downloads the Android SDK.
   Pick Standard install and accept the licenses.
2. On the welcome screen go to More Actions, then Virtual Device
   Manager (or press Cmd/Ctrl+Shift+A and type "Device Manager").
3. Click Create Device, pick **Pixel 10** (1080x2424, the resolution
   this repo's coordinates are calibrated for), click Next.
4. Pick a system image: choose a recent release **with Google Play**
   in its name (not just Google APIs). The Play variant lets you
   install Hinge straight from the Play Store. Download it if asked,
   then Finish.
5. Press the Play button next to your new Pixel 10 to boot it. First
   boot takes a minute or two.
6. Confirm your computer sees it (exactly one device should list):

       adb devices
       # emulator-5554    device

If a physical Android phone is plugged in over USB, unplug it now.
Every script here calls plain `adb ...`, which errors out with two
devices attached ("more than one device/emulator").

## 5. Install Hinge on the emulator

Easiest first: open the Play Store app inside the emulator, sign in,
search Hinge, install. (Needs the Google Play system image from step
4 and a Google account. Any account works; it is only for the store.)

Alternatives if Play is unavailable:

- Drag a Hinge `.apk` file onto the emulator window, or run
  `adb install hinge.apk`.
- Split APKs pulled from a phone (Play installs apps as a base APK
  plus config splits) must be installed as a set:

      adb install-multiple base.apk split_config.arm64_v8a.apk split_config.xxhdpi.apk

  To pull them off your own phone: enable USB debugging on the phone,
  then `adb -s <phone-serial> shell pm path co.hinge.app` lists the
  paths, and `adb -s <phone-serial> pull <path> .` copies each one.
  Use `-s` to target the phone while the emulator also runs.

Then open Hinge in the emulator, sign in with your **throwaway**
account, finish onboarding, and leave the app on the **Discover tab**
(the compass icon, bottom nav).

Free Hinge allows about 8 likes per day (resets 4am local). Hinge+
has no cap. This matters in step 10.

## 6. Pick a judge backend

Set `JUDGE_BACKEND` in `config.py`. The loop is identical either way;
only judgment speed, quality, and cost change.

| Backend | Key | Default model | Speed | Cost |
|---|---|---|---|---|
| `ollama` (local) | none (`ollama serve` + pulled model) | `qwen3-vl:8b-instruct` | ~7 min/profile | $0 |
| `gemini` (default) | `GEMINI_API_KEY` (AI Studio free tier) | `gemini-3.5-flash-lite` | ~2 s/judge | $0 |
| `anthropic` | `ANTHROPIC_API_KEY` (+ optional `ANTHROPIC_BASE_URL`) | `claude-sonnet-4-6` | seconds | ~$0.02-0.05/profile |
| `openai` | `OPENAI_API_KEY` + `OPENAI_BASE_URL` | `gpt-4o-mini` | seconds | provider pricing |

Copy `.env.example` to `.env` and fill in ONLY the key for your
backend. Never commit `.env` (it is gitignored).

Backend notes:

- **Gemini (recommended start).** Get a key at Google AI Studio
  (aistudio.google.com/apikey), free tier is enough. Put it in `.env`
  as `GEMINI_API_KEY`. If openers disappoint, try `GEMINI_MODEL =
  "gemini-3.8-flash"` in config.
- **Ollama (fully local, private).** Install Ollama, then:

      ollama serve
      ollama pull qwen3-vl:8b-instruct

  Keep `OLLAMA_NUM_CTX = 32768` in config: 7 full-res screenshots
  overflow Ollama's 4K default context. Use the `-instruct` tag, not
  the thinking variant (its long reasoning traces stretch each
  judgment to minutes). Needs roughly 10 GB free RAM while running.
- **Anthropic.** Claude API key as `ANTHROPIC_API_KEY`. You can point
  `ANTHROPIC_BASE_URL` at any Anthropic-compatible endpoint instead.
- **OpenAI-compatible slot.** Set `OPENAI_BASE_URL` (OpenAI, Groq,
  OpenRouter, etc.), `OPENAI_MODEL`, and `OPENAI_API_KEY`. The model
  MUST accept images and support tool calls. Always smoke-test before
  going live: run the judge on a couple of screenshots and confirm a
  valid structured decision comes back (see Troubleshooting).

What did not work for us, so you do not repeat it: abliteration.ai's
Anthropic surface (4-image cap, rejected tall stitched frames, flaky
forced tool calls) and Groq keys exposing text-only models (fast but
blind to screenshots).

## 7. Calibrate tap coordinates

`config.COORDS` ships tuned for a Pixel 10 at 1080x2424. If that is
your emulator and Hinge has not reshuffled its layout, the values work
as-is. Verify instead of assuming:

1. With Hinge open on the Discover tab, run:

       python calibrate.py

   It saves `calibrate.png` in the repo folder.
2. Open it in a viewer that shows cursor pixel coordinates (Preview's
   inspector on Mac, Paint on Windows).
3. Check these spots and update `config.py` for any that miss:

   - `skip_button` - the X on the profile card (advances profiles)
   - `heart_photo_1` - fallback only; hearts are re-found per profile
     by `vision.py` because their height shifts per layout
   - `send_like_button` / `comment_input` - fallbacks; also re-found
     live on the compose card
   - `scroll_from` / `scroll_to` - the scroll swipe gesture
   - `nav_discover` etc. - the 5 bottom-nav icons
   - `sliders_icon` / `age_chip` - filter row (only for `--set-filters`)
   - `self_avatar`, `view_tab`, `back_arrow` - only for `scan_self.py`

## 8. Write your mode (rubric)

Do not edit the examples in place. Copy the closer one and make it
yours:

    cp modes/example_lenient.py modes/mine.py

- `example_lenient.py` - default LIKE, skips only bots, spam, and
  empty profiles. Start here for volume.
- `example_strict.py` - default SKIP, likes only on a specific strong
  hook. Start here for selectivity.

Edit `PREFERENCES` in your own words - that text is the actual judging
rubric. Then in your mode file:

- `AGE_MIN` / `AGE_MAX` - optional judge-side age gate (or leave None
  and rely on Hinge's in-app filter).
- `MESSAGE_VOICE` - `"example_casual"`, `"example_polished"`, or a
  custom string. This controls opener style.
- `PREMADES` - optional verbatim openers the judge may paste instead
  of writing fresh. Leave `[]` to disable.
- `MAX_LIKES_PER_SESSION` - 5 is a sane first-run cap on Hinge+.
  Leave 8 on free Hinge (your whole daily allowance).

Set `ACTIVE_MODE = "mine"` in `config.py` (or pass
`python main.py --mode mine` per run).

Dry-run guidance by tier:

- Free Hinge: set `DRY_RUN = True` for the first run or two. It logs
  decisions but force-skips every would-be like, so your 8/day cap
  survives rubric tuning. Flip back to False after.
- Hinge+: stay live with the small cap and Ctrl-C the moment a
  decision looks off. No dry-run needed.

## 9. Optional: check your own profile first

Before the loop touches anyone else, ToS-clean step that also proves
your coordinates work:

    python scan_self.py --save-frames

It taps through to your profile's View tab (what others see), captures
it, asks the model for photo/prompt improvements, returns to Discover,
and writes `debug/self_scan_<timestamp>.md`. Fixing weak photos or
prompts beats any rubric tuning.

## 10. First live run

1. Confirm: Hinge open on Discover, one `adb devices` entry, venv
   active, `.env` has your key, `ACTIVE_MODE` points at your mode.
2. Start it:

       python main.py

3. Watch the printed decisions live: name, like/skip, reasoning,
   opener. Stop with Ctrl-C if anything looks wrong (weird opener, a
   like that should be a skip).
4. Review `debug/session_log.jsonl` (one JSON line per profile with
   timing, tokens, cost) and the `debug/liked|skipped/` frame folders.
5. Edit `PREFERENCES`/voice based on what you saw and re-run. On free
   Hinge you wait for the 4am cap reset between batches; on Hinge+
   you can iterate immediately and later raise the cap to 25-50.

Handy flags: `--mode X` (one-shot mode override), `--set-filters`
(drives the in-app age slider to your mode's band; needs
`filter_coords.json` from `calibrate_filters.py`), `--location CITY`
and `--rotate NAME` (city switching/rotation; needs
`location_coords.json` + `locations.json`, Hinge+ for out-of-area).

## 11. Costs (measured, Oct 2026)

- Local Ollama: $0. About 20 s capture + 7 min judge + 1 min act
  per profile.
- Gemini free tier: $0. About 2 s per judgment, full loop under
  2 min/profile.
- Anthropic Sonnet at list pricing: roughly $0.02-0.05/profile.
  Estimates print per profile and as running totals.

## 12. How it works under the hood

- `main.py` - loop runner: capture, judge (3 tries, halts on
  auth/billing errors instead of swiping blind), act, log.
  Duplicate-frame detection force-skips when Hinge does not advance.
- `judge_common.py` - backend-agnostic prompt assembly, the
  `submit_decision` schema, `Decision` dataclass, `pack_frames` (for
  image-capped providers), `sanitize_message` (typing-layer safety).
- `judge.py` / `judge_gemini.py` / `judge_openai.py` /
  `judge_ollama.py` - one module per backend, same contract.
- `vision.py` - blob detection for hearts and the Send Like pill.
- `metrics.py` - per-profile JSONL + cost math.
- `matches_scan.py` - Matches-tab analytics (Anthropic only).

## 13. Troubleshooting

- `more than one device/emulator`: unplug the phone, or
  `export ANDROID_SERIAL=emulator-5554`.
- No device found: emulator not booted, or USB debugging off on a
  physical device.
- Judge fails 3 times: loop skips the profile to stay alive; check
  key, quota, and model name.
- Likes never fire: test `vision.find_first_heart` on a screenshot.
  Hinge restyles buttons between builds; the detector covers white
  discs, black discs, and glyph fallback, in that priority.
- `typed text didn't reach expected pixel density`: host CPU
  contention dropping key events. Close heavy apps; chunked typing
  plus the density check usually still lands it, and the like sends
  anyway.
- Empty Discover ("seen everyone"): with `--rotate` the loop moves
  to the next city; otherwise you are done for now.
- `compose_close` in config is an unused leftover; the loop never
  closes compose without sending.
- Slow Ollama: confirm `OLLAMA_NUM_CTX = 32768` and the `-instruct`
  tag; the thinking variant is minutes per judgment.

## 14. Fork changelog vs upstream

- New `judge_gemini.py` and `judge_openai.py`; `JUDGE_BACKEND` now
  routes local (`ollama`) vs cloud (`gemini` / `anthropic` / `openai`).
- Backend-aware cost estimates; full key matrix in `.env.example`.
- Black-circle + glyph-fallback heart detection; typing sanitizer and
  chunking; small-model output clamps; frame packing for capped APIs.
- Personal `modes/mine.py` starter; this README rewrite.

## 15. License

MIT, inherited from upstream.
