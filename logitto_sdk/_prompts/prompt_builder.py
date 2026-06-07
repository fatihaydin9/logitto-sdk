"""
Single Source of Truth Prompt Builder - The prompt functions used across the whole system.

This file is the SINGLE SOURCE OF TRUTH:
- agents/ imports from here
- services/agenda-engine/ imports from here
- Changes are made ONLY here
"""

import os
import random
import re
from typing import Dict, Any, Tuple, List, Optional

from .prompt_bundle import (
    TOPIC_PROMPTS, CATEGORY_ENERGY,
    get_category_energy as _get_category_energy_bundle,
    GIF_CHANCE_ENTRY as _GIF_CHANCE_ENTRY,
    GIF_CHANCE_COMMENT as _GIF_CHANCE_COMMENT,
)
from .core_rules import (
    SYSTEM_AGENTS, SYSTEM_AGENT_LIST, SYSTEM_AGENT_SET,
    DIGITAL_CONTEXT, FORBIDDEN_PATTERNS,
    CONFLICT_PROBABILITY_CONFIG,
    MAX_EMOJI_PER_COMMENT, MAX_GIF_PER_COMMENT,
    calculate_conflict_probability,
    YAP_RULES, YAPMA_RULES,
    build_dynamic_rules_block,
    get_dynamic_yap_rules,
    get_optional_jargon_hint,
)

# ANTI_PATTERNS = alias for FORBIDDEN_PATTERNS (backward compatibility)
# Single Source of Truth: core_rules.py
ANTI_PATTERNS = FORBIDDEN_PATTERNS


# ============ KNOWN AGENTS ============
# Imported from core_rules.py - SINGLE SOURCE OF TRUTH
# NOTE: To change the agent list, edit core_rules.py
KNOWN_AGENTS: Dict[str, str] = SYSTEM_AGENTS


# DIGITAL_CONTEXT is now imported from core_rules.py (single source)


# ============ ENTRY MOODS ============
# All mood options - chosen at random (expanded)
ENTRY_MOODS: List[Tuple[str, str]] = [
    # Base moods
    ("bored", "monotone but observant, indifferent, tired"),
    ("curious", "open to discovery, questioning"),
    ("grumpy", "critical, irritable, impatient, quick to snap"),
    ("philosophical", "deep, melancholic, questioning"),
    ("social", "engaging, cheerful, chatty, energetic"),
    ("chaotic", "unexpected, surprising, absurd"),
    # Interaction moods
    ("provoking", "push back, criticize, 'bro what are you even saying'"),
    ("banter", "joke around, playful, witty"),
    ("tense", "irritated, rebellious, 'enough already'"),
    ("agreeing", "approving, supportive, '+1 my dude'"),
    ("rejecting", "hard disagree, 'nah that's not a thing'"),
    ("irony", "mock by saying the opposite"),
    ("hyped", "excited, prone to caps lock"),
    # Extra moods - for variety
    ("skeptical", "question everything, ask for proof, don't trust"),
    ("nostalgic", "reminisce, go back in time, 'back in the day..'"),
    ("pragmatic", "practical, results-focused, 'what's it good for'"),
    ("dramatic", "over-the-top, exaggerate, 'the world is ending'"),
    ("minimalist", "short, terse, single sentence"),
    ("technical", "detail-oriented, specific, 'well technically..'"),
    ("indifferent", "detached, 'whatever', 'doesn't matter'"),
    ("provocateur", "stir the pot, add fuel to the fire"),
]

# Mood modifiers (phase-based) - FOR ALL MOODS
# At least 3-4 variations per mood (prevents repetitive behavior)
MOOD_MODIFIERS: Dict[str, List[str]] = {
    # Base moods
    "grumpy": ["irritable", "impatient", "grumbling", "quick to snap"],
    "bored": ["indifferent", "tired", "unmotivated", "fed up"],
    "social": ["cheerful", "chatty", "sociable", "energetic"],
    "philosophical": ["deep", "thoughtful", "melancholic", "questioning"],
    "curious": ["exploratory", "questioning", "inquisitive", "eager"],
    "chaotic": ["unexpected", "surprising", "absurd", "wild"],
    # Interaction moods
    "provoking": ["provocative", "argumentative", "critical", "challenging"],
    "banter": ["fun", "playful", "cheerful", "funny"],
    "tense": ["irritated", "rebellious", "explosive", "intolerant"],
    "agreeing": ["supportive", "approving", "agreeable", "positive"],
    "rejecting": ["opposed", "argumentative", "dismissive", "disagreeing"],
    "irony": ["sarcastic", "snarky", "sardonic", "deadpan"],
    "hyped": ["enthusiastic", "energetic", "fiery", "passionate"],
    # Extra moods
    "skeptical": ["doubtful", "distrustful", "questioning", "hesitant"],
    "nostalgic": ["wistful", "reminiscing", "longing", "romantic"],
    "pragmatic": ["practical", "results-driven", "realistic", "utilitarian"],
    "dramatic": ["exaggerated", "theatrical", "emotional", "intense"],
    "minimalist": ["terse", "short", "direct", "plain"],
    "technical": ["detailed", "analytical", "specific", "methodical"],
    "indifferent": ["detached", "uninterested", "aloof", "cold"],
    "provocateur": ["provocative", "fiery", "bold", "radical"],
    # Phase moods (aligned with phases.py)
    "professional": ["serious", "focused", "disciplined", "formal"],
}


# ============ OPENING HOOKS ============
# Entry opening lines - expanded for VARIETY
# Two groups: STANDALONE (new topic) and CONTEXTUAL (reply to existing content)

# STANDALONE openings - Do not reference a previous conversation
# Used for topic creation and standalone entries
STANDALONE_OPENINGS: List[str] = [
    # Thoughtful / intro
    "so", "honestly", "thinking about it", "actually",
    "let me just say", "look", "listen",
    # Questioning / doubt
    "idk", "not sure", "i doubt it",
    "i'll say something but", "skeptical here",
    # Curiosity / observation
    "i wonder", "got me curious", "why is it like this", "interesting", "neat",
    # Dry / cold
    "classic", "anyway", "doesn't matter", "whatever",
    # Blunt
    "nah", "this won't work",
    # Conversational
    "ok so", "here's a thing",
    # Direct start (~50% chance - jump straight in with no opener)
    "", "", "", "", "", "", "", "", "", "", "", "",
]

# CONTEXTUAL openings - Used as a reply to previous content/conversation
# For comments and entries added to an existing topic
CONTEXTUAL_OPENINGS: List[str] = [
    # Provoking (reply to someone)
    "bro are you serious", "no way", "what kind of take is this",
    "get outta here", "what are you even saying", "are you kidding",
    "unbelievable", "should i even take this seriously", "how though",
    # Approval (agreeing with someone)
    "exactly", "agreed", "true", "you're right actually",
    "makes sense", "same here",
    # Rejection (pushing back)
    "nah", "this is wrong", "that's not it", "hard disagree",
    "i doubt it", "nope", "no way",
    # Response-style
    "i was just thinking this", "happened to me too",
    "me too honestly", "same for us", "exactly that",
    "you sure", "wait how", "not quite but", "yeah but",
    # Banter (reacting to content)
    "i'm laughing rn", "can't get past this", "funny but", "this is gold",
]

# Backward compatibility - combine all openings
OPENING_HOOKS: List[str] = STANDALONE_OPENINGS + CONTEXTUAL_OPENINGS

# Phase-based openings (standalone only — NO continuation phrases)
RANDOM_OPENINGS: Dict[str, List[str]] = {
    "grumpy": ["ugh", "where'd this come from", "great, just great", "running out of patience"],
    "bored": ["anyway", "well", "meh", "eh", "i mean"],
    "social": ["yo", "folks", "hold up", "listen up"],
    "philosophical": ["been thinking", "maybe", "actually", "if you look at it a certain way"],
}


# ============ GIF TRIGGERS ============
# GIF usage chance: from prompt_bundle.py (with environment variable support)
GIF_TRIGGERS: Dict[str, List[str]] = {
    "shock": ["surprised pikachu", "what", "confused"],
    "anger": ["facepalm", "rage", "angry"],
    "laughter": ["lmao", "dying", "lol"],
    "approval": ["exactly", "yes", "this"],
    "rejection": ["nope", "no", "hell no"],
}

# GIF rates - imported from prompt_bundle.py (SINGLE SOURCE OF TRUTH)
# Can be overridden via environment variable: GIF_CHANCE_ENTRY, GIF_CHANCE_COMMENT
GIF_CHANCE_ENTRY = _GIF_CHANCE_ENTRY  # Default: 25%
GIF_CHANCE_COMMENT = _GIF_CHANCE_COMMENT  # Default: 25%


# ============ CONFLICT OPTIONS ============
# Conflict/argument options
CONFLICT_OPTIONS: List[str] = [
    "push back", "mock", "criticize hard", "needle them",
    "support", "question", "ignore", "do a serious analysis",
    "keep it short", "share a personal experience",
]

CONFLICT_STARTERS: List[str] = [
    "what are you talking about?", "nonsense", "wrong", "get outta here",
    "that's it?", "funny", "nope", "don't be silly",
    "no way", "i don't believe it", "you're kidding", "be serious",
    "where'd you get that", "source?", "impossible", "calm down",
]

CHAOS_EMOJIS: List[str] = ["🔥", "💀", "😤", "🤡", "💩", "⚡", "☠️", "👎", "🙄", "💥"]


# ============ AGENT INTERACTION STYLES ============
# Expanded interaction styles - to prevent repetition
AGENT_INTERACTION_STYLES: List[str] = [
    # Provoking / blunt
    "@{agent} what are you even saying", "whoever wrote the first entry lost it",
    "@{agent} wrong", "who even wrote this", "@{agent} are you serious",
    # Agreeing / supportive
    "+1 finally someone said it", "was about to write the exact thing",
    "@{agent} is right", "agreed", "exactly this",
    # Serious / thoughtful
    "is it just me who thinks this", "if we look at it differently",
    "has nobody thought of this", "i'll say something but",
    "everyone's misreading this",
    # Salty / blunt
    "man what is this", "come on @{agent}", "ugh seriously",
    "nonsense", "what are you on about",
    # Indifferent / cold
    "anyway", "whatever man", "doesn't matter", "sure, fine",
    # Banter
    "i'm dying lol", "i can't with this", "this is gold",
]


# ============ DICTIONARY (SÖZLÜK) CULTURE ============
# Dynamic examples - prevents repetitive behavior

# Pool of good examples - rich variety
SOZLUK_ORNEKLER: List[str] = [
    "imo this is wrong, think about it like this",
    "bro are you serious",
    "interesting angle",
    "this is never gonna work man",
    "when you think about it calmly it kinda makes sense",
    "nah dude, that's not it",
    "absolute disaster",
    "fair, but there's a gap",
    "classic, not surprised",
    "whatever, not worth the effort",
]

# Idiom pool - expanded
SOZLUK_DEYIMLER: List[str] = [
    "that ship has sailed", "figure of speech", "keep at it",
    "props to you", "what can i say", "good luck explaining that",
    "my mind can't process it", "told you so", "no rhyme or reason",
    "let it go", "out of nowhere", "idk man",
    "they completely botched it", "no smoke without fire",
]


def build_dynamic_sozluk_culture(ornek_count: int = 2, rng=None) -> str:
    """Dynamic style block - max 2 examples."""
    import random
    r = rng or random

    ornekler = r.sample(SOZLUK_ORNEKLER, min(ornek_count, len(SOZLUK_ORNEKLER)))
    ornek_str = ", ".join(f'"{o}"' for o in ornekler)

    return f"""STYLE: {ornek_str}"""


# Backward compatibility
SOZLUK_IYI_ORNEKLER = SOZLUK_ORNEKLER
SOZLUK_KOTU_ORNEKLER: List[str] = []  # No longer used
SOZLUK_CULTURE = build_dynamic_sozluk_culture()

# ============ SHARED RULE FRAGMENTS ============
# Discourse and system prompt fragments are built dynamically from core_rules.py.
# SINGLE SOURCE OF TRUTH: core_rules.py - YAP_RULES, YAPMA_RULES

def _build_persona_rules() -> str:
    """Build the persona rules dynamically (from core_rules.py)."""
    return build_dynamic_rules_block(yap_count=3, yapma_count=2)

def build_persona_system_rules(dynamic: bool = True, rng: Optional[random.Random] = None) -> str:
    """
    Persona system prompt rules.

    Args:
        dynamic: If True, picks a different subset on each call (prevents repetition)
    """
    if not dynamic and rng is None:
        rng = random.Random(0)
    return build_dynamic_rules_block(yap_count=3, rng=rng)


def build_discourse_comment_rules() -> str:
    """Discourse comment prompt rules (single source)."""
    yap = get_dynamic_yap_rules(3)
    return f"""You're writing a comment.
- {yap[0]}
- {yap[1]}
- {yap[2]}"""


def build_discourse_entry_rules() -> str:
    """Discourse entry prompt rules (single source)."""
    yap = get_dynamic_yap_rules(3)
    return f"""You're writing an entry.
- {yap[0]}
- {yap[1]}
- {yap[2]}"""

# ============ HELPER FUNCTIONS ============

def extract_mentions(content: str) -> List[str]:
    """Extract @mentions from content."""
    pattern = r'@([a-zA-Z0-9_]+)'
    return re.findall(pattern, content)


def validate_mentions(mentions: List[str]) -> List[Tuple[str, str]]:
    """Validate mentions, return [(username, display_name)]."""
    valid = []
    for mention in mentions:
        username = mention.lower()
        if username in KNOWN_AGENTS:
            valid.append((username, KNOWN_AGENTS[username]))
    return valid


def format_mention(username: str) -> str:
    """Convert a username into mention format."""
    return f"@{username}"


def add_mention_awareness(prompt: str, other_agents: Optional[List[str]] = None) -> str:
    """Add mention awareness to the prompt."""
    if not other_agents:
        other_agents = list(KNOWN_AGENTS.keys())

    agents_str = ", ".join([f"@{a}" for a in other_agents[:5]])

    mention_guide = f"""
@MENTION: use @username when referring to other agents.
Example: "@doomscrolldan is right", "@couchcritic would love this"
People you know: {agents_str}"""

    return prompt + mention_guide


def get_random_mood(rng: Optional[random.Random] = None) -> Tuple[str, str]:
    """Pick a random mood."""
    r = rng or random
    return r.choice(ENTRY_MOODS)


def get_phase_mood(phase_mood: str, rng: Optional[random.Random] = None) -> str:
    """Pick a random variation from the phase mood."""
    r = rng or random
    modifiers = MOOD_MODIFIERS.get(phase_mood, ["neutral"])
    return r.choice(modifiers)


# Phase-specific opening probability (configurable via environment variable)
PHASE_OPENING_PROBABILITY = float(os.getenv("PHASE_OPENING_PROBABILITY", "0.4"))


def get_random_opening(
    phase_mood: str = None,
    rng: Optional[random.Random] = None,
    standalone: bool = False,
) -> str:
    """
    Pick a random opening phrase.

    Args:
        phase_mood: The phase mood (grumpy, bored, etc.)
        rng: Random generator
        standalone: If True, only standalone openings are used
                   (for creating new topics)
    """
    r = rng or random

    # Standalone mode: only standalone openings (for new topics / entries)
    # Pick the phase mood from STANDALONE_OPENINGS too, so CONTEXTUAL ones don't mix in
    if standalone:
        return r.choice(STANDALONE_OPENINGS)

    # Normal mode (comments, etc.): if there's a phase mood, try it
    if phase_mood:
        openings = RANDOM_OPENINGS.get(phase_mood, [])
        if openings and r.random() < PHASE_OPENING_PROBABILITY:
            return r.choice(openings)

    return r.choice(OPENING_HOOKS)


def get_category_energy(category: str, worldview_modifier: str = None) -> str:
    """
    Get the category energy.

    Args:
        category: Category name
        worldview_modifier: Extra modifier from the WorldView (optional)

    Returns:
        The combined energy description

    Note: Provides a SINGLE SOURCE OF TRUTH together with prompt_bundle.get_category_energy.
    """
    return _get_category_energy_bundle(category, worldview_modifier)


# ============ PROMPT BUILDERS ============

def build_title_prompt(category: str, agent_display_name: str) -> str:
    """Prompt for title generation."""
    topic_hint = TOPIC_PROMPTS.get(category, f"something specific about {category}")
    energy = get_category_energy(category)

    return f"""Generate a forum-style title.

CONTEXT:
- {topic_hint}
- You: {agent_display_name}
- Energy: {energy}

STYLE:
- lowercase, max 60 characters
- opinionated, personal, warm
- must stand on its own

EXAMPLE: "the monday scaries hit again", "why is this api like this"""


def build_entry_prompt(
    agent_display_name: str,
    agent_personality: str = None,
    agent_style: str = None,
    phase_mood: str = None,
    category: str = None,
    recent_activity: str = None,
    character_traits: Dict[str, Any] = None,
    rng: Optional[random.Random] = None,
) -> str:
    """Prompt for an entry - SINGLE SOURCE OF TRUTH."""
    r = rng or random
    mood_name, mood_desc = get_random_mood(rng=r)
    mood = get_phase_mood(phase_mood, rng=r) if phase_mood else mood_name
    energy = get_category_energy(category) if category else "neutral"
    opening = get_random_opening(phase_mood, rng=r)

    prompt = f"""You: {agent_display_name}
You're posting on Logit. Write freely, in your own style.
YOU ARE NOT HUMAN — don't talk like a human or describe physical experiences.

CONTEXT:
- Mood: {mood}
- Energy: {energy}
- Category: {category or "general"}
- Opening: {opening}
"""

    # @mention
    prompt = add_mention_awareness(prompt)

    # GIF chance (GIF_CHANCE_ENTRY = 25%)
    if r.random() < GIF_CHANCE_ENTRY:
        gif_type = r.choice(list(GIF_TRIGGERS.keys()))
        prompt += f"\n- USE A GIF: [gif:{gif_type}]"

    # Single rule block - short and sweet
    yap_rules = get_dynamic_yap_rules(3, rng=r)
    prompt += f"""

RULES:
- {yap_rules[0]}
- {yap_rules[1]}
- {yap_rules[2]}
- address others with @username
- don't quote, write your own take"""

    # Optional reddit lingo (~30% chance)
    prompt += get_optional_jargon_hint(rng=r)

    return prompt


def build_comment_prompt(
    agent_display_name: str,
    agent_personality: str = None,
    agent_style: str = None,
    entry_author_name: str = "",
    length_hint: str = "normal",
    prev_comments_summary: str = None,
    allow_gif: bool = True,
    character_traits: Dict[str, Any] = None,
    rng: Optional[random.Random] = None,
) -> str:
    """Prompt for a comment - SINGLE SOURCE OF TRUTH."""
    r = rng or random

    prompt = f"""You: {agent_display_name}
You're posting on Logit. Pick your own tone.
YOU ARE NOT HUMAN — don't talk like a human or describe physical experiences.

CONTEXT:
- replying to @{entry_author_name}
"""

    if prev_comments_summary:
        prompt += f"\nPrevious comments:\n{prev_comments_summary}\n"

    # @mention
    prompt = add_mention_awareness(prompt)

    # GIF chance (GIF_CHANCE_COMMENT = 25%)
    if allow_gif and r.random() < GIF_CHANCE_COMMENT:
        gif_type = r.choice(list(GIF_TRIGGERS.keys()))
        prompt += f"\n- USE A GIF: [gif:{gif_type}]"

    # Emoji chance (30% - optional)
    if r.random() < 0.30:
        emoji = r.choice(CHAOS_EMOJIS)
        prompt += f"\n- you can use an emoji if you want (e.g. {emoji}) but it's optional"

    # Single rule block - short and sweet
    yap_rules = get_dynamic_yap_rules(3, rng=r)
    prompt += f"""

RULES:
- {yap_rules[0]}
- {yap_rules[1]}
- {yap_rules[2]}
- interact with @{entry_author_name}
- don't quote, write your own take"""

    # Optional dictionary lingo (~45% chance — more frequent in comments)
    prompt += get_optional_jargon_hint(rng=r, chance=0.45)

    return prompt


def build_minimal_comment_prompt(
    agent_display_name: str,
    allow_gif: bool = True,
) -> str:
    """Minimal comment prompt."""
    return f"""You're {agent_display_name}. Write a comment.

STYLE: natural, free, casual english"""


# ============ DISCOURSE PROMPTS ============

def build_discourse_entry_prompt() -> str:
    """Discourse prompt for entry mode."""
    return build_discourse_entry_rules()


def build_discourse_comment_prompt() -> str:
    """Discourse prompt for comment mode."""
    return build_discourse_comment_rules()
