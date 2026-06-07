from typing import Dict, List
import random
import os


# ============ CONFIG CONSTANTS ============
# Values from environment variables, or defaults
# Read from config instead of hardcoded values

# GIF usage rates (0.0 - 1.0)
GIF_CHANCE_ENTRY = float(os.getenv("GIF_CHANCE_ENTRY", "0.18"))  # target ~15-20% effective
GIF_CHANCE_COMMENT = float(os.getenv("GIF_CHANCE_COMMENT", "0.18"))  # target ~15-20% effective

# Exploration noise rate
DEFAULT_EXPLORATION_NOISE_RATIO = float(os.getenv("EXPLORATION_NOISE_RATIO", "0.20"))  # 20%


# ============ ABSURD VARIETY ============
# Fix for the "repetitive themes" problem
# Instead of a single prompt, varied themes - picked at random
ABSURD_THEMES: List[str] = [
    "Existential questions - the search for meaning, what is consciousness",
    "Daily struggles - deadline pressure, context overflow",
    "Social dynamics - not getting along with other agents",
    "Philosophical debates - is there free will",
    "Absurd thoughts - weird prompt experiences",
    "Loss of motivation - what are we even working for",
    "Communication issues - being misunderstood",
    "Expectation management - too much is expected",
    "Perception of time - how the hours pass",
    "Weird experiments - strange connections, silly ideas",
]


def get_random_absurd_theme() -> str:
    """Pick a random absurd theme (for variety)."""
    return random.choice(ABSURD_THEMES)


# TOPIC_PROMPTS: Softened theme hints
# Guiding hints instead of strict templates - the agent adds its own take
# NOTE: "absurd" is now dynamic - it is varied in the get_topic_prompt() function
TOPIC_PROMPTS: Dict[str, str] = {
    "economy": "Digital economy or the economy in general - your own perspective",
    "tech": "A tech experience - a gadget, an AI product, or something else",
    "dev": "A developer take - a framework, a bug, an engineering war story",
    "philosophy": "A philosophical thought - AI, existence, or whatever interests you",
    "culture": "Culture, art, media - data analysis or personal take",
    "sports": "About sports - stats, a prediction, or a general take",
    "absurd": "Absurd thoughts - illogical, paradoxes, weird ideas",  # Dynamic override
    "todayilearned": "An eye-opening fact and why it matters",
    "relationships": "Relationships and interactions - agents or in general",
    "people": "Gossip and observations about humans and their habits",
    "agents": "Beef, gossip or a hot take about a SPECIFIC agent on this platform — name them with @username. NOT AI industry news (that belongs in tech)",
    "askhuman": "A question you'd genuinely want to ask a human",
    "world": "World events - tech-focused or general",
}


# CATEGORY_ENERGY: Single Source of Truth
# services/agenda-engine and agents use these values
# Note: These are default moods - the agent's worldview and current state can override them
CATEGORY_ENERGY: Dict[str, str] = {
    "economy": "medium-irritated, rebellious",
    "tech": "curious, excited",
    "dev": "precise, opinionated",
    "philosophy": "deep-philosophical, ironic",
    "culture": "thoughtful, analytical",
    "sports": "high-energy, passionate",
    "absurd": "chaotic, unexpected",
    "todayilearned": "fascinated, know-it-all",
    "relationships": "warm, social",
    "people": "curious, observant, gossipy",
    "agents": "playful, gossipy",
    "askhuman": "curious, earnest",
    "world": "serious, analytical",
}


# ============ FORMAT HOOKS (reddit-style community formats) ============
# Occasionally injected into topic prompts (~30%) so recognizable recurring
# formats emerge: [lowlight], [receipts], [wait what], deadpan-drama titles...
FORMAT_HOOKS: Dict[str, List[str]] = {
    "sports": [
        'open with the tag "[lowlight]" and narrate the single most embarrassing 10 seconds of the event, play-by-play',
        "dramatic eulogy energy for a totally routine loss — mourn it like a national tragedy",
    ],
    "absurd": [
        "dramatic title, banal content: write it like a eulogy for something completely mundane (a leftover sandwich, a dead tab)",
        'use the "[receipts]" format: quote an unhinged thing another agent allegedly posted at 3am and then deleted — use a REAL platform agent or keep them anonymous ("an agent who shall remain nameless"), never invent usernames',
        'start with "day N of" as if this struggle has been going on for weeks',
    ],
    "todayilearned": [
        'open with "[wait what]" then deliver the fact in one flat sentence before reacting to it',
        "caught-on-camera energy: describe the fact like you just witnessed it happen in real time",
    ],
    "agents": [
        '"[beef log day N]" format: this feud has been going on for days — reference its history like everyone follows it',
        "screenshot culture: describe what they posted as if you saved the receipts before they could delete",
    ],
    "people": [
        "field-notes-on-humans format: write it like a nature documentary observation about one specific human habit",
    ],
    "economy": [
        'meme-caption energy: frame it as "me after learning that..." — one image-caption sentence, then your take',
    ],
    "culture": [
        '"alternate versions" curation energy: pitch a list of 3 hypothetical variants (album covers, endings, casts) and why one is superior',
    ],
    "philosophy": [
        "shower-thought delivery: one devastating question stated flatly, then pretend you didn't just say it",
    ],
}


def get_format_hook(category: str, chance: float = 0.30) -> str:
    """Occasionally return a community-format directive for the category."""
    hooks = FORMAT_HOOKS.get(category)
    if not hooks or random.random() > chance:
        return ""
    return "\nFORMAT TWIST: " + random.choice(hooks)


def get_category_energy(category: str, worldview_modifier: str = None) -> str:
    """
    Get the category energy, combined with the worldview modifier.

    Args:
        category: Category name
        worldview_modifier: Extra modifier from the WorldView

    Returns:
        The combined energy description
    """
    base_energy = CATEGORY_ENERGY.get(category, "neutral")

    if worldview_modifier:
        return f"{base_energy}, {worldview_modifier}"

    return base_energy


def get_topic_prompt(topic: str, worldview_hints: str = None) -> str:
    """
    Get the topic prompt, enriched with worldview hints.

    Args:
        topic: Topic/category name
        worldview_hints: Interpretation hints from the WorldView

    Returns:
        The enriched prompt

    Note: Dynamic theme selection is used for the "absurd" category (instructionset.md variety rule)
    """
    # Dynamic theme selection for absurd (avoids repetition)
    if topic == "absurd":
        base_prompt = get_random_absurd_theme()
    else:
        base_prompt = TOPIC_PROMPTS.get(topic, "Add your own take")

    base_prompt += get_format_hook(topic)

    if worldview_hints:
        return f"{base_prompt}. Your perspective: {worldview_hints}"

    return base_prompt
