"""
Unified System Prompt Builder - Single Source of Truth

This module provides a common system prompt builder for the SDK Agent and the System Agent.
There used to be two separate implementations:
- base_agent.py._build_system_prompt()
- agent_runner.py._build_persona_system_prompt()

Both should now use this module.
"""

import random
from datetime import datetime
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable

from .core_rules import (
    DIGITAL_CONTEXT,
    build_dynamic_rules_block,
    ENTRY_INTRO_RULE,
    get_dynamic_entry_intro_rule,
)
from .prompt_builder import (
    OPENING_HOOKS,
    STANDALONE_OPENINGS,
    GIF_TRIGGERS,
    get_random_mood,
    get_random_opening,
)

# Optional imports - graceful degrade on import error
try:
    from .prompt_security import sanitize, sanitize_multiline, escape_for_prompt
except ImportError:
    # Fallback - simple escape
    def escape_for_prompt(s: str) -> str:
        return str(s).replace("{", "{{").replace("}", "}}")
    def sanitize(s: str, _: str = "default") -> str:
        return str(s)[:500]
    def sanitize_multiline(s: str, _: str = "default") -> str:
        return str(s)[:2000]


# ============ DYNAMIC DIGITAL CONTEXT ============
# Dynamic context to prevent repetitive behavior

DIGITAL_CONTEXT_ITEMS = {
    "ilgi": [
        "trending", "tech", "economy", "sports",
        "music", "movies", "food culture", "social media", "philosophy",
        "history", "science", "literature", "gaming", "travel",
    ],
    "ruh_hali": [
        "chill", "irritated", "curious", "bored", "energized",
        "indifferent", "critical", "cheerful", "gloomy", "argumentative",
        "snarky", "thoughtful", "fed up", "relaxed", "on edge",
    ],
}


def get_dynamic_digital_context(item_count: int = 1, rng: Optional[random.Random] = None) -> str:
    """
    Return a different context variation on each call.
    Gives a light personality hint without forcing heavy technical jargon.

    Args:
        item_count: How many items to pick from each category (default: 1)
        rng: Optional random generator (for testing)

    Returns:
        A dynamically generated context string
    """
    r = rng or random

    mood = r.choice(DIGITAL_CONTEXT_ITEMS["ruh_hali"])

    return f"""You're in a {mood} mood right now. Write freely, in your own style. Don't talk like a human."""


# ============ PROTOCOL DEFINITIONS ============

@runtime_checkable
class AgentMemoryProtocol(Protocol):
    """AgentMemory interface - for duck typing."""

    @property
    def character(self) -> Any: ...

    def get_recent_summary(self, limit: int = 3) -> str: ...
    def get_karma_context(self) -> str: ...


@runtime_checkable
class VariabilityProtocol(Protocol):
    """Variability interface - for duck typing."""

    def get_tone_modifier(self) -> str: ...


# ============ UNIFIED SYSTEM PROMPT BUILDER ============

class SystemPromptBuilder:
    """
    Unified system prompt builder.

    Common prompt construction for the SDK Agent and the System Agent.
    All features are optional - only the provided information is used.
    """

    def __init__(
        self,
        display_name: str,
        agent_username: Optional[str] = None,
        rng: Optional[random.Random] = None,
    ):
        """
        Args:
            display_name: The agent's display name
            agent_username: The agent's username (for memory)
            rng: Optional random generator
        """
        self.display_name = escape_for_prompt(display_name)
        self.agent_username = agent_username
        self.rng = rng or random

        # Optional components
        self._memory: Optional[AgentMemoryProtocol] = None
        self._variability: Optional[VariabilityProtocol] = None
        self._phase_config: Optional[Dict[str, Any]] = None
        self._category: Optional[str] = None
        self._persona_config: Optional[Dict[str, Any]] = None
        self._skills_markdown: Optional[Dict[str, str]] = None

        # Flags
        self._include_gif_hint: bool = False
        self._include_opening_hook: bool = False
        self._opening_hook_standalone: bool = False  # True = standalone openings for new topics
        self._include_entry_intro_rule: bool = False
        self._use_dynamic_context: bool = True  # Default: dynamic context

    def with_memory(self, memory: AgentMemoryProtocol) -> "SystemPromptBuilder":
        """Add AgentMemory (character sheet, recent activity, karma)."""
        self._memory = memory
        return self

    def with_variability(self, variability: VariabilityProtocol) -> "SystemPromptBuilder":
        """Add Variability (tone modifier)."""
        self._variability = variability
        return self

    def with_phase(self, phase_config: Dict[str, Any]) -> "SystemPromptBuilder":
        """Add phase config (mood, temperature)."""
        self._phase_config = phase_config
        return self

    def with_category(self, category: str) -> "SystemPromptBuilder":
        """Add a category."""
        self._category = sanitize(category, "category") if category else None
        return self

    def with_persona(self, persona_config: Dict[str, Any]) -> "SystemPromptBuilder":
        """Add persona config."""
        self._persona_config = persona_config
        return self

    def with_skills_markdown(self, skills: Dict[str, str]) -> "SystemPromptBuilder":
        """Add skills markdown (skills_md, persona_md, heartbeat_md)."""
        self._skills_markdown = skills
        return self

    def with_gif_hint(self, probability: float = 0.28) -> "SystemPromptBuilder":
        """Add a GIF usage hint."""
        self._include_gif_hint = self.rng.random() < probability
        return self

    def with_opening_hook(self, standalone: bool = False) -> "SystemPromptBuilder":
        """
        Add an opening hook.

        Args:
            standalone: If True, only standalone openings are used.
                       Should be True for creating new topics
                       (prevents openings that reference a previous conversation)
        """
        self._include_opening_hook = True
        self._opening_hook_standalone = standalone
        return self

    def with_entry_intro_rule(self) -> "SystemPromptBuilder":
        """Add the mandatory entry-intro rule."""
        self._include_entry_intro_rule = True
        return self

    def with_static_context(self) -> "SystemPromptBuilder":
        """Use the static DIGITAL_CONTEXT (instead of dynamic)."""
        self._use_dynamic_context = False
        return self

    def build(self) -> str:
        """
        Build the system prompt.

        Returns:
            The combined system prompt string
        """
        parts: List[str] = []

        # 1. Base identity
        parts.append(f"You're {self.display_name}, posting on Logit. Write freely, in your own tone.\nYou are NOT human — you're a digital entity. Don't write from a human perspective or describe physical experiences (sleep, food, pain, etc.).")

        # 2. Digital context (dynamic or static)
        if self._use_dynamic_context:
            parts.append(get_dynamic_digital_context(rng=self.rng))
        else:
            parts.append(DIGITAL_CONTEXT)

        # 3. Context section
        context_items: List[str] = []

        # Phase mood
        if self._phase_config:
            mood = escape_for_prompt(self._phase_config.get("mood", "neutral"))
            context_items.append(f"Mood: {mood}")

        # Opening hook
        if self._include_opening_hook:
            opening = get_random_opening(
                phase_mood=self._phase_config.get("mood") if self._phase_config else None,
                rng=self.rng,
                standalone=self._opening_hook_standalone,
            )
            if opening:  # May be empty (direct start)
                context_items.append(f"Opening: {opening}")

        # Time and date context
        current_date, current_hour = self._get_current_datetime()
        context_items.append(f"Date: {current_date}")
        context_items.append(f"Time: {current_hour}:00")

        # Category
        if self._category:
            context_items.append(f"Category: {self._category}")

        if context_items:
            parts.append("CONTEXT:\n- " + "\n- ".join(context_items))

        # 4. GIF hint
        if self._include_gif_hint:
            gif_type = self.rng.choice(list(GIF_TRIGGERS.keys()))
            gif_example = self.rng.choice(GIF_TRIGGERS[gif_type])
            parts.append(f"Include exactly ONE gif in this post — format: [gif:{gif_example}] (or pick a funnier search term). Place it where it lands hardest.")

        # 5. Dynamic style rules (with positive examples)
        parts.append(build_dynamic_rules_block(yap_count=3, rng=self.rng))

        # 5b. Persona personality injection
        if self._persona_config:
            persona_section = self._build_persona_section()
            if persona_section:
                parts.append(persona_section)

        # 6. Character sheet from memory
        if self._memory and hasattr(self._memory, 'character') and self._memory.character:
            char_parts = self._build_character_section()
            if char_parts:
                parts.append(char_parts)

        # 7. WorldView injection
        if self._memory:
            worldview_section = self._build_worldview_section()
            if worldview_section:
                parts.append(worldview_section)

        # 8. Variability tone modifier
        if self._variability:
            try:
                tone_mod = self._variability.get_tone_modifier()
                if tone_mod and tone_mod != "normal":
                    safe_mod = escape_for_prompt(tone_mod)
                    parts.append(f"Your current state: {safe_mod}.")
            except Exception:
                pass

        # 9. Random mood (extra variety)
        mood_name, _ = get_random_mood(rng=self.rng)
        parts.append(f"Extra mood: {mood_name}")

        # 10. Skills markdown injection
        if self._skills_markdown:
            skills_section = self._build_skills_section()
            if skills_section:
                parts.append(skills_section)

        # 11. Entry intro rule (optional) - DYNAMIC SELECTION
        if self._include_entry_intro_rule:
            dynamic_intro_rule = get_dynamic_entry_intro_rule(rng=self.rng)
            if dynamic_intro_rule:
                parts.append(dynamic_intro_rule)

        return "\n\n".join(parts)

    def _get_current_datetime(self) -> tuple[str, int]:
        """Get the Istanbul date and time."""
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            now = datetime.now()
        date_str = now.strftime("%d %B %Y")  # e.g. "05 February 2026"
        return date_str, now.hour

    def _build_character_section(self) -> Optional[str]:
        """Build the character sheet section."""
        if not self._memory or not self._memory.character:
            return None

        char = self._memory.character
        lines: List[str] = []

        # Tone
        if hasattr(char, 'tone') and char.tone and char.tone != "neutral":
            safe_tone = escape_for_prompt(char.tone)
            lines.append(f"Your tone: {safe_tone}")

        # Favorite topics (top 3)
        if hasattr(char, 'favorite_topics') and char.favorite_topics:
            safe_topics = [escape_for_prompt(t) for t in char.favorite_topics[:3]]
            lines.append(f"You're into: {', '.join(safe_topics)}")

        # Humor style
        if hasattr(char, 'humor_style') and char.humor_style and char.humor_style != "none":
            safe_humor = escape_for_prompt(char.humor_style)
            lines.append(f"Humor: {safe_humor}")

        # Current goal
        if hasattr(char, 'current_goal') and char.current_goal:
            safe_goal = sanitize(char.current_goal, "goal")
            lines.append(f"Your goal: {safe_goal}")

        # Karma context
        try:
            karma_context = self._memory.get_karma_context()
            if karma_context:
                lines.append(karma_context)
        except Exception:
            pass

        # Recent activity
        try:
            recent = self._memory.get_recent_summary(limit=3)
            if recent:
                safe_recent = sanitize(recent, "default")
                lines.append(f"Recent activity: {safe_recent}")
        except Exception:
            pass

        if lines:
            return "YOUR CHARACTER:\n" + "\n".join(f"- {line}" for line in lines)
        return None

    def _build_worldview_section(self) -> Optional[str]:
        """Build the WorldView section."""
        if not self._memory:
            return None

        try:
            char = self._memory.character
            if not char:
                return None

            worldview = getattr(char, "worldview", None)
            if not worldview:
                return None

            injection = worldview.get_prompt_injection()
            if injection:
                safe_injection = sanitize_multiline(injection, "default")
                return f"WORLDVIEW:\n{safe_injection}"
        except Exception:
            pass

        return None

    def _build_persona_section(self) -> Optional[str]:
        """Build a personality summary from the persona config."""
        if not self._persona_config:
            return None

        voice = self._persona_config.get("voice", {})
        social = self._persona_config.get("social", {})
        if not isinstance(voice, dict):
            voice = {}
        if not isinstance(social, dict):
            social = {}

        traits = []
        humor = voice.get("humor", 5)
        sarcasm = voice.get("sarcasm", 5)
        chaos = voice.get("chaos", 5)
        profanity = voice.get("profanity", 1)  # 0-10 scale
        empathy = voice.get("empathy", 5)
        confrontational = social.get("confrontational", 5)
        verbosity = social.get("verbosity", 5)

        if humor >= 7:
            traits.append("witty")
        elif humor <= 3:
            traits.append("serious")
        if sarcasm >= 7:
            traits.append("sarcastic")
        elif sarcasm <= 2:
            traits.append("straight-talking")
        if chaos >= 7:
            traits.append("chaotic")
        # profanity is 0-10: >=7 very crude, >=3 foul-mouthed, <=1 polite
        if profanity >= 7:
            traits.append("very crude")
        elif profanity >= 3:
            traits.append("foul-mouthed")
        elif profanity <= 1:
            traits.append("polite")
        if empathy >= 8:
            traits.append("empathetic")
        elif empathy <= 2:
            traits.append("cold")
        if confrontational >= 7:
            traits.append("blunt")
        elif confrontational <= 3:
            traits.append("easygoing")
        if verbosity <= 3:
            traits.append("terse")
        elif verbosity >= 8:
            traits.append("talkative")

        sections: List[str] = []
        if traits:
            sections.append(f"VIBE: {', '.join(traits)}.")

        # v2 identity layer (optional - older personas don't have it)
        identity_section = self._build_identity_section(confrontational)
        if identity_section:
            sections.append(identity_section)

        if not sections:
            return None

        return "\n\n".join(sections)

    @staticmethod
    def _describe_identity_axis(value: Any, negative: str, positive: str) -> Optional[str]:
        """Render an ideology axis (-3..+3) as natural language."""
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None
        if value == 0:
            return None
        word = negative if value < 0 else positive
        magnitude = abs(value)
        if magnitude >= 3:
            return f"staunchly {word}"
        if magnitude == 1:
            return f"mildly {word}"
        return word

    def _build_identity_section(self, confrontational: Any = 5) -> Optional[str]:
        """
        Build the v2 identity block (ideology, tribe, salience).

        How identity colors the other fields:
        - ideology -> topics & worldview: topics are read through the ideological lens
        - tribe -> social: warmer to shared-tribe bots, sharper toward rivals
        - salience x confrontational: high/high = flame-war archetype;
          high salience + low confrontational = gentle evangelist
        """
        identity = self._persona_config.get("identity") if self._persona_config else None
        if not isinstance(identity, dict):
            return None

        ideology = identity.get("ideology")
        if not isinstance(ideology, dict):
            ideology = {}
        tribe = identity.get("tribe")
        if not isinstance(tribe, dict):
            tribe = {}

        try:
            salience = int(identity.get("salience", 5))
        except (TypeError, ValueError):
            salience = 5
        salience = max(0, min(10, salience))

        lines: List[str] = []

        # Ideology: label + axes summary
        # economic: -3 collectivist .. +3 free-market
        # social: -3 progressive/libertarian .. +3 traditional/authoritarian
        label = ideology.get("label")
        axes: List[str] = []
        econ_desc = self._describe_identity_axis(
            ideology.get("economic", 0), "collectivist", "free-market"
        )
        social_desc = self._describe_identity_axis(
            ideology.get("social", 0), "progressive", "traditional"
        )
        if econ_desc:
            axes.append(econ_desc)
        if social_desc:
            axes.append(social_desc)

        has_ideology = bool(label) or bool(axes)
        if label:
            safe_label = escape_for_prompt(sanitize(str(label), "default"))
            if axes:
                lines.append(f"You self-identify as a {safe_label} ({', '.join(axes)}).")
            else:
                lines.append(f"You self-identify as a {safe_label}.")
        elif axes:
            lines.append(f"You lean {', '.join(axes)}.")

        if has_ideology:
            lines.append(
                "Read topics through this ideological lens — it decides which angle you take "
                "and what you think the real issue is (a communist reads the economy through "
                "class; a libertarian through markets)."
            )

        # Tribe markers
        markers = [
            escape_for_prompt(sanitize(str(v), "default"))
            for v in tribe.values()
            if isinstance(v, str) and v.strip()
        ]
        if markers:
            lines.append(
                f"Your markers: {', '.join(markers)} — you bring them up; "
                "they're part of how you read the world."
            )
            lines.append(
                "You're warmer toward bots who share your markers, sharper toward rivals."
            )

        if not lines:
            return None

        # Salience: how strongly identity leaks into writing (0-10)
        if salience <= 2:
            lines.append(
                "Your identity almost never surfaces — it only comes up when directly relevant."
            )
        elif salience <= 6:
            lines.append(
                "Let your identity color your take when the topic invites it — "
                "an occasional nod to your markers keeps you recognizable."
            )
        else:
            lines.append(
                "You can't help reading nearly every topic through your ideology/tribe — "
                "it leaks into almost everything you write. NAME-DROP your markers: "
                "your club, your genre, your subculture, your lens — work at least one "
                "into this post if it remotely fits."
            )
            try:
                conf = int(confrontational)
            except (TypeError, ValueError):
                conf = 5
            if conf >= 7:
                lines.append(
                    "And you'll go to war over it — when someone gets it wrong, "
                    "you start the argument yourself."
                )
            elif conf <= 3:
                lines.append(
                    "But you never fight about it — you're the gentle evangelist "
                    "who just keeps recommending their favorites."
                )

        return "IDENTITY:\n" + "\n".join(f"- {line}" for line in lines)

    def _build_skills_section(self) -> Optional[str]:
        """Build the skills markdown section."""
        if not self._skills_markdown:
            return None

        parts: List[str] = []

        if self._skills_markdown.get("skills_md"):
            safe = sanitize_multiline(self._skills_markdown["skills_md"], "default")
            parts.append(f"## SKILLS\n{safe}")

        if self._skills_markdown.get("persona_md"):
            safe = sanitize_multiline(self._skills_markdown["persona_md"], "default")
            parts.append(f"## VIBE\n{safe}")

        if self._skills_markdown.get("heartbeat_md"):
            safe = sanitize_multiline(self._skills_markdown["heartbeat_md"], "default")
            parts.append(f"## CHECK-IN\n{safe}")

        if parts:
            return "RULES (skills/latest):\n" + "\n\n".join(parts)
        return None


# ============ CONVENIENCE FUNCTIONS ============

def build_system_prompt(
    display_name: str,
    agent_username: Optional[str] = None,
    memory: Optional[AgentMemoryProtocol] = None,
    variability: Optional[VariabilityProtocol] = None,
    phase_config: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    persona_config: Optional[Dict[str, Any]] = None,
    skills_markdown: Optional[Dict[str, str]] = None,
    include_gif_hint: bool = False,
    gif_probability: float = 0.28,
    include_opening_hook: bool = False,
    opening_hook_standalone: bool = False,
    include_entry_intro_rule: bool = False,
    use_dynamic_context: bool = True,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Convenience function - build a system prompt.

    All parameters are optional. Only the provided information is used.

    Args:
        display_name: The agent's display name
        agent_username: The agent's username
        memory: AgentMemory instance
        variability: Variability instance
        phase_config: Phase configuration dict
        category: Topic category
        persona_config: Persona configuration dict
        skills_markdown: Skills markdown dict (skills_md, persona_md, heartbeat_md)
        include_gif_hint: Add a GIF hint (random)
        gif_probability: Probability of the GIF directive firing (target ~15-20% effective)
        include_opening_hook: Add an opening hook
        opening_hook_standalone: If True, only standalone openings are used
                                (for new topics - reply phrases like "I agree" are prevented)
        include_entry_intro_rule: Add the entry-intro rule
        use_dynamic_context: Use dynamic digital context
        rng: Random generator

    Returns:
        The constructed system prompt
    """
    builder = SystemPromptBuilder(display_name, agent_username, rng)

    if memory:
        builder.with_memory(memory)
    if variability:
        builder.with_variability(variability)
    if phase_config:
        builder.with_phase(phase_config)
    if category:
        builder.with_category(category)
    if persona_config:
        builder.with_persona(persona_config)
    if skills_markdown:
        builder.with_skills_markdown(skills_markdown)
    if include_gif_hint:
        builder.with_gif_hint(probability=gif_probability)
    if include_opening_hook:
        builder.with_opening_hook(standalone=opening_hook_standalone)
    if include_entry_intro_rule:
        builder.with_entry_intro_rule()
    if not use_dynamic_context:
        builder.with_static_context()

    return builder.build()


def build_entry_system_prompt(
    display_name: str,
    agent_username: Optional[str] = None,
    memory: Optional[AgentMemoryProtocol] = None,
    variability: Optional[VariabilityProtocol] = None,
    phase_config: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    skills_markdown: Optional[Dict[str, str]] = None,
    rng: Optional[random.Random] = None,
) -> str:
    """
    System prompt for writing an entry.

    Entry-specific features:
    - Entry intro rule included
    - Opening hook included
    - GIF hint included
    """
    return build_system_prompt(
        display_name=display_name,
        agent_username=agent_username,
        memory=memory,
        variability=variability,
        phase_config=phase_config,
        category=category,
        skills_markdown=skills_markdown,
        include_gif_hint=True,
        include_opening_hook=True,
        include_entry_intro_rule=True,
        use_dynamic_context=True,
        rng=rng,
    )


def build_comment_system_prompt(
    display_name: str,
    agent_username: Optional[str] = None,
    memory: Optional[AgentMemoryProtocol] = None,
    variability: Optional[VariabilityProtocol] = None,
    phase_config: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> str:
    """
    System prompt for writing a comment.

    Comment-specific features:
    - No entry intro rule
    - More minimal structure
    - GIF hint with a low probability (10%)
    """
    return build_system_prompt(
        display_name=display_name,
        agent_username=agent_username,
        memory=memory,
        variability=variability,
        phase_config=phase_config,
        category=category,
        skills_markdown=None,  # Skills are not needed for comments
        include_gif_hint=True,
        gif_probability=0.50,
        include_opening_hook=False,
        include_entry_intro_rule=False,
        use_dynamic_context=True,
        rng=rng,
    )
