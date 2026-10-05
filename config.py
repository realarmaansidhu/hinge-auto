"""Configuration for HingeAuto.

PREFERENCES, AGE_MIN/MAX, and MESSAGE_VOICE come from the active mode (see
`modes/`). Set ACTIVE_MODE here for the persistent default; override per-run
via `python main.py --mode <name>`.

The COORDS defaults below are calibrated for a Pixel 10 emulator
(1080x2424). If that's what you're running and Hinge hasn't shifted
its layout, they should work as-is. Otherwise run `python calibrate.py`
and update the values that don't match your device.
"""

from pathlib import Path

# ---------- Mode selection ----------
# Which `modes/<name>.py` to load. Overridden per-run by `python main.py --mode X`.
ACTIVE_MODE = "mine"

# These get filled in by _apply_mode() at the bottom of this file. Declared
# here so static analyzers / IDEs see them. Do not edit by hand — edit the
# mode module instead.
PREFERENCES: str = ""
AGE_MIN: int | None = None
AGE_MAX: int | None = None
MESSAGE_VOICE: str | None = None
MODE_NAME: str = ""
PREMADES: list[dict] = []

# ---------- Run mode ----------
# DRY_RUN = False -> actually like / send messages (default)
# DRY_RUN = True  -> decide and log, but force-skip every profile
#                    instead of liking. Every "would-like" profile gets
#                    skipped (gone from your queue) but no likes are
#                    spent.
#
# When to flip this to True:
#   - Free Hinge (8 likes/day): YES, for your first run or two. Lets
#     you watch decisions without spending your daily cap on a rubric
#     you haven't tuned. Once decisions look right, flip back to False.
#   - Hinge+ (unlimited likes): NO. Just run small live batches
#     (MAX_LIKES_PER_SESSION = 5) and Ctrl-C if something looks off.
DRY_RUN = False

# Default = 8, which matches free-tier Hinge's daily like cap (resets at
# 4am local). One session per day exhausts the free allotment cleanly.
#
# If you have Hinge+ (no daily cap), bump this to ~25-50 per session and
# run multiple sessions throughout the day. Going much higher per session
# tends to trigger Hinge's soft-throttle (empty Discover after a burst);
# spacing batches across the day works better than one giant batch.
MAX_LIKES_PER_SESSION = 8
MAX_PROFILES_PER_SESSION = 100

# ---------- Emulator settings ----------
# Pixel 10 (and recent Pixel models) are 1080x2424. Change if you're using
# a different emulator profile — and re-run calibrate.py after any change.
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2424

# Number of scroll-and-screenshot passes per profile.
# Longer profiles (6 photos + 3 prompts) need ~7 frames at the scroll step
# below. Duplicate end frames on shorter profiles are harmless.
FRAMES_PER_PROFILE = 7

# ---------- Coordinates ----------
# Pixel 10 emulator defaults (1080x2424). These values are
# accurate for the standard Pixel 10 AVD; if your screen is the same
# resolution and Hinge's layout hasn't shifted, they'll work as-is. If
# anything is off, run `python calibrate.py` to capture a screenshot and
# update the values that don't match.
COORDS = {
    # Skip / like action targets (Discover screen, photo 1 at top)
    "skip_button":       (134, 2068),   # X icon on prompt/photo card
    "heart_photo_1":     (938, 1421),   # Heart icon on photo 1

    # Compose box (anchors to the element whose heart was tapped; these
    # values are mostly fallbacks — vision.py re-finds them at tap-time
    # because the box shifts per profile).
    "send_like_button":  (687, 1488),
    "comment_input":     (540, 1317),
    "compose_close":     (960, 200),

    # Scroll gesture (swipe up = scroll down through profile).
    "scroll_from":       (540, 1700),
    "scroll_to":         (540, 700),
    "scroll_duration_ms": 350,

    # Bottom nav (5 evenly-spaced icons across the bottom strip).
    "nav_discover":      (108, 2270),
    "nav_standouts":     (324, 2270),
    "nav_likes_you":     (540, 2270),
    "nav_matches":       (756, 2270),
    "nav_self_pfp":      (972, 2270),

    # Self-profile flow (used by scan_self.py — "what does my profile
    # look like to others"). From Discover: nav_self_pfp → self_avatar →
    # view_tab gets you to a scrollable view of your own profile. Then
    # back_arrow → back_arrow → nav_discover to return.
    "self_avatar":       (540, 497),    # circle avatar on self tab
    "view_tab":          (810, 310),    # 'View' tab on profile editor
    "back_arrow":        (65, 200),     # top-left back arrow

    # Discover filter row (tap the chip to open its bottom sheet).
    "sliders_icon":      (95, 225),     # opens Dating Preferences
    "age_chip":          (460, 225),    # opens Age filter sheet
}

# ---------- Timing ----------
# Random delay between actions (seconds, min/max for jitter).
DELAYS = {
    "after_scroll":     (0.6, 1.0),
    "after_screenshot": (0.2, 0.4),
    "after_tap":        (0.8, 1.4),
    "after_like_sent":  (2.5, 4.0),
    "after_skip":       (1.5, 2.5),
}

# ---------- Judge backend ----------
# Two routes:
#   LOCAL: "ollama"  -> on-laptop, free, private. Needs `ollama serve` +
#                       a pulled vision model. Slow (~7 min/profile).
#   CLOUD: one of the below, chosen by which key you hold. All fast
#          (~seconds/profile). The loop only needs vision + forced tools.
#     "gemini"     -> AI Studio free tier (GEMINI_API_KEY). DEFAULT.
#     "anthropic"  -> Claude API (ANTHROPIC_API_KEY). Reference quality.
#     "openai"     -> generic OpenAI-compatible slot: OpenAI, Groq,
#                     OpenRouter, ... (OPENAI_API_KEY + OPENAI_BASE_URL).
# NOTE: we pointed the "anthropic" route at abliteration.ai's compatible
# surface and dropped it - 4-image cap, tall-stitch 413s, and its gateway
# intermittently ignores forced tool calls. Any *other* Anthropic-compatible
# endpoint can still be used via ANTHROPIC_BASE_URL.
JUDGE_BACKEND = "gemini"

# ---------- Anthropic settings (when JUDGE_BACKEND == "anthropic") ----------
# Sonnet is the reference default. Point ANTHROPIC_BASE_URL at any
# Anthropic-compatible endpoint to use a third-party key instead.
MODEL = "claude-sonnet-4-6"
EFFORT = "medium"  # low | medium | high

# ---------- Ollama settings (when JUDGE_BACKEND == "ollama") ----------
# Vision-capable models that handle multiple images per turn:
#   "qwen3-vl:8b-instruct" - same 8B weights, no thinking trace. ~13s/judgment
#                         warm on M-series, correct structured output.
#                         DEFAULT. (Validated 2026-10-04.)
#   "qwen3-vl:8b"       - thinking variant: correct but ~7 min/judgment
#                         (3K-trace tokens). Avoid for the loop.
#   "qwen2.5-vl"        - previous-gen default (7B); fallback if qwen3-vl
#                         misbehaves on tool calls.
#   "llama3.2-vision"   — alternative; tool-calling can be flakier
OLLAMA_MODEL = "qwen3-vl:8b-instruct"

# 7 full-res screenshots per profile need headroom over Ollama's default
# 4K context. 32K fits comfortably in 24GB unified memory alongside an 8B
# model. Lower to 16384 if prefill feels slow.
OLLAMA_NUM_CTX = 32768

# OLLAMA_HOST: None or "" -> default http://localhost:11434
#              "https://ollama.com" -> Ollama Cloud (requires OLLAMA_API_KEY)
# Can also be set via the OLLAMA_HOST environment variable.
OLLAMA_HOST = None

# ---------- Gemini settings (when JUDGE_BACKEND == "gemini") ----------
# Needs GEMINI_API_KEY (or GOOGLE_API_KEY) in .env - AI Studio free tier.
#   "gemini-3.5-flash-lite" - fastest/cheapest multimodal Flash. DEFAULT.
#   "gemini-3.8-flash"      - most intelligent Flash; use if lite's judgment
#                             or openers disappoint.
GEMINI_MODEL = "gemini-3.5-flash-lite"

# ---------- OpenAI-compatible settings (when JUDGE_BACKEND == "openai") ----------
# Bring-your-own-cloud-key slot. Point at any OpenAI-dialect endpoint:
#   OpenAI:            https://api.openai.com/v1  (gpt-4o / gpt-4o-mini)
#   Groq:              https://api.groq.com/openai/v1
#   OpenRouter:        https://openrouter.ai/api/v1
# Key via OPENAI_API_KEY in .env (or OPENAI_BASE_URL env as override).
# CAUTION: the model MUST be vision-capable with tool support. Groq keys
# we tested expose text-only models (tool envelope validated, image path
# not) - always run a judge smoke test before going live (see module docs).
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o-mini"

# ---------- Paths ----------
BASE_DIR = Path(__file__).parent
DEBUG_DIR = BASE_DIR / "debug"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SAVE_DEBUG_FRAMES = True  # keep frames + decisions in debug/ for review


def _apply_mode() -> None:
    """Resolve ACTIVE_MODE and populate this module's PREFERENCES /
    AGE_MIN / AGE_MAX / MESSAGE_VOICE / MODE_NAME / cap overrides.

    Re-entrant — main.py calls this again after parsing --mode so a CLI
    override takes effect before the judge sees config.
    """
    import modes
    mode = modes.load(ACTIVE_MODE)
    g = globals()
    g["PREFERENCES"] = mode.PREFERENCES
    g["AGE_MIN"] = getattr(mode, "AGE_MIN", None)
    g["AGE_MAX"] = getattr(mode, "AGE_MAX", None)
    g["MESSAGE_VOICE"] = getattr(mode, "MESSAGE_VOICE", None)
    g["MODE_NAME"] = mode.NAME
    g["PREMADES"] = list(getattr(mode, "PREMADES", []))
    for k in ("MAX_LIKES_PER_SESSION", "MAX_PROFILES_PER_SESSION"):
        v = getattr(mode, k, None)
        if v is not None:
            g[k] = v


_apply_mode()
