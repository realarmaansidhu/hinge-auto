"""Personal mode - lenient baseline with a polished voice.

Starting point copied from `example_lenient`: default LIKE, skip only on
clear bot / spam / empty signals. PREFERENCES below is a scaffold -
iterate on it after watching the first live run (see debug/session_log.jsonl).

Voice: "example_polished" (see voice/example_polished.py). No age gate;
Hinge's in-app filter handles that.
"""

NAME = "mine"
DESCRIPTION = "Personal lenient baseline; polished openers; no age gate."

AGE_MIN = None
AGE_MAX = None

MESSAGE_VOICE = "example_polished"

# Hinge+: small batch while the rubric is untuned. Raise to 25-50 once
# decisions look right. (Free-tier users: leave at 8 - the daily cap.)
MAX_LIKES_PER_SESSION = 5
MAX_PROFILES_PER_SESSION = None

# Verbatim openers the judge may pick instead of writing fresh. Empty =
# disabled; add your own {id, message, use_when} entries as you find
# lines that work.
PREMADES = []

PREFERENCES = """
Default decision: LIKE.

Be generous - a missed like costs much less than a missed match. The
vast majority of profiles should be liked.

Skip ONLY when one of these clearly applies:

1. The profile looks fake / bot-like / spam. Telltale signs: only one
   photo and it looks AI-generated or stock; bio is a single off-platform
   handle ("snap me at X", "find me on TikTok @Y"); the photos and the
   stated info contradict each other in obvious ways.

2. The profile is genuinely empty - no readable prompt answers, no
   meaningful bio, photos are all unrecognizable (e.g. only blurry group
   shots or pets, no person visible).

3. Explicit deal-breaker statements that put you well outside the
   intended audience. Do not invent deal-breakers that aren't actually
   stated on the profile.

Everything else is a LIKE. Specifically:

- Career, hobbies, vibe, photo quality, group dynamics, distance, height,
  whether they drink, what they post about - none of these are skip
  signals in this mode.

- If the profile is OK but you can't think of a strong, specific opener,
  output decision=like with message="" and message_archetype="empty".
  A like with no message is better than a skip.

When writing the reasoning field:
- Reference concrete details ("photo 3 shows...", "the [prompt] answer
  about X").
- Stay neutral and non-judgmental about people.
"""
