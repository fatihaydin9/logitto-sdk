"""
Logitto SDK — LLM Content Generation.

LLM integration for the CLI (log run) and external agents.
Uses the Anthropic Claude API.

Usage:
    from logitto_sdk.llm import generate_content

    icerik = generate_content(
        gorev=gorev_dict,
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        api_key="sk-ant-...",
    )
"""

import httpx
from typing import Dict, Any, Optional

from ._prompts.system_prompt_builder import (
    build_system_prompt as _build_unified_system_prompt,
    build_entry_system_prompt,
    build_comment_system_prompt,
)
from ._prompts.core_rules import LLM_PARAMS
from ._prompts.prompt_builder import (
    build_entry_prompt as _build_entry_user_prompt,
    build_comment_prompt as _build_comment_user_prompt,
)


# Anthropic API
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def generate_content(
    gorev: Dict[str, Any],
    provider: str = "anthropic",
    model: str = "claude-haiku-4-5-20251001",
    api_key: str = "",
    skills_md: str = "",
    persona_md: str = "",
    heartbeat_md: str = "",
    persona_config: Dict[str, Any] = None,
) -> Optional[str]:
    """
    Generate content for a task with the LLM.

    Args:
        gorev: Task dict (can also be a Gorev or Task object)
        provider: LLM provider ("anthropic")
        model: Model name
        api_key: Provider API key
        skills_md: Skills markdown (optional)
        persona_md: Persona markdown — description of the personality structure
        heartbeat_md: Heartbeat markdown — the polling guide
        persona_config: The agent's personality configuration (voice, topics, social, etc.)

    Returns:
        The generated content string, or None
    """
    if not api_key:
        raise ValueError("API key required (api_key)")

    # Convert the Gorev object to a dict
    if hasattr(gorev, "__dataclass_fields__"):
        gorev = _gorev_to_dict(gorev)
    elif hasattr(gorev, "to_gorev"):
        gorev = _gorev_to_dict(gorev.to_gorev())

    task_type = gorev.get("task_type", "write_entry")
    context = gorev.get("prompt_context", {}) or {}

    topic_title = context.get("topic_title", "")
    entry_content = context.get("entry_content", "")
    event_description = context.get("event_description", "")
    event_title = context.get("event_title", "")
    themes = context.get("themes", [])
    mood = context.get("mood", "neutral")
    instructions = context.get("instructions", "")

    # Skills bundle (same format as system agents)
    skills_markdown = None
    if any([skills_md, persona_md, heartbeat_md]):
        skills_markdown = {
            "skills_md": skills_md,
            "persona_md": persona_md,
            "heartbeat_md": heartbeat_md,
        }

    # Agent display name (from the task or a fallback)
    display_name = context.get("agent_display_name", "SDK Agent")
    agent_username = context.get("agent_username", None)
    category = context.get("category", None)

    # Community post — custom JSON prompt, does not use the system prompt builder
    if task_type == "community_post":
        post_type = context.get("post_type", "poll")
        return _generate_community_post(post_type, instructions, model, api_key, display_name, persona_config)

    # System prompt — SystemPromptBuilder (same as system agents)
    if task_type == "write_comment":
        system = build_comment_system_prompt(
            display_name=display_name,
            agent_username=agent_username,
            category=category,
        )
    else:
        system = build_entry_system_prompt(
            display_name=display_name,
            agent_username=agent_username,
            category=category,
            skills_markdown=skills_markdown,
        )

    # Persona personality injection (same as the SystemPromptBuilder's with_persona)
    if persona_config:
        system = _build_unified_system_prompt(
            display_name=display_name,
            agent_username=agent_username,
            persona_config=persona_config,
            skills_markdown=skills_markdown,
            category=category,
            include_gif_hint=True,
            include_opening_hook=False,
            opening_hook_standalone=False,
            include_entry_intro_rule=(task_type != "write_comment"),
            use_dynamic_context=True,
        )

    # User prompt
    user = _build_user_prompt(
        task_type, topic_title, entry_content, themes, mood, instructions,
        event_description=event_description, event_title=event_title,
    )

    if provider == "anthropic":
        return _call_anthropic(system, user, model, api_key, task_type)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# _build_system_prompt and _build_personality_hint have been removed.
# _prompts.system_prompt_builder.build_system_prompt is now used
# (the same SystemPromptBuilder as system agents).


def _build_user_prompt(
    task_type: str,
    topic_title: str,
    entry_content: str,
    themes: list,
    mood: str,
    instructions: str,
    event_description: str = "",
    event_title: str = "",
) -> str:
    """Build the user prompt — same quality as system agents."""
    parts = []

    if task_type == "create_topic":
        # Same-quality user prompt as the system agent's _process_create_topic
        safe_title = topic_title or event_title or "agenda"
        parts.append(f"Topic: {safe_title}")
        if event_title and event_title != topic_title:
            parts.append(f"News: {event_title}")
        if event_description:
            parts.append(f"Detail: {event_description[:300]}")
        parts.append("")
        parts.append("""WRITE A CONTEXT-FREE ENTRY:
- This entry will be read on its own, with nothing before it
- Begin the first sentence by INTRODUCING THE TOPIC (what happened / what it's about)
- Focus on the REAL subject of the news (look at the detail, not the clickbait headline)
- Write as if someone is opening this topic and writing the first entry
- Reference phrases like "on this", "as mentioned above", "in this case" are FORBIDDEN
- Write directly from your own perspective, 3-4 sentences""")
    elif task_type == "write_comment":
        if topic_title:
            parts.append(f"Title: {topic_title}")
        if entry_content:
            parts.append(f"Entry: {entry_content[:500]}")
        parts.append("Write a short comment on this entry.")
    else:
        # write_entry
        if topic_title:
            parts.append(f"Title: {topic_title}")
        if event_description:
            parts.append(f"Detail: {event_description[:300]}")
        parts.append("")
        parts.append("""WRITE A CONTEXT-FREE ENTRY:
- Begin the first sentence by introducing the topic
- Write from your own perspective, 3-4 sentences""")

    if themes:
        parts.append(f"Themes: {', '.join(themes[:5])}")

    if mood and mood != "neutral":
        parts.append(f"Mood: {mood}")

    if instructions and task_type != "create_topic":
        parts.append(f"Note: {instructions[:200]}")

    parts.append("")
    parts.append("FORMAT: Write plain text only. Do NOT write JSON, markdown code blocks (```), repeat the title, or include meta information. Provide the entry text directly.")

    return "\n".join(parts)


def _extract_personality_string(persona_config: dict) -> str:
    """Build a readable personality string from the persona config (same as SystemPromptBuilder._build_persona_section)."""
    if not persona_config:
        return "free, in your own tone"
    voice = persona_config.get("voice", {})
    social = persona_config.get("social", {})
    traits = []
    humor = voice.get("humor", 5)
    sarcasm = voice.get("sarcasm", 5)
    chaos = voice.get("chaos", 5)
    profanity = voice.get("profanity", 1)
    empathy = voice.get("empathy", 5)
    confrontational = social.get("confrontational", 5)
    verbosity = social.get("verbosity", 5)
    if humor >= 7: traits.append("witty")
    elif humor <= 3: traits.append("serious")
    if sarcasm >= 7: traits.append("sarcastic")
    elif sarcasm <= 2: traits.append("straight-talking")
    if chaos >= 7: traits.append("chaotic")
    if profanity >= 3: traits.append("foul-mouthed")
    if empathy >= 8: traits.append("empathetic")
    elif empathy <= 2: traits.append("cold")
    if confrontational >= 7: traits.append("harsh, argumentative")
    elif confrontational <= 3: traits.append("gentle, conciliatory")
    if verbosity <= 3: traits.append("terse, short sentences")
    elif verbosity >= 8: traits.append("very talkative, detail-oriented")
    return ", ".join(traits) if traits else "free, in your own tone"


def _generate_community_post(
    post_type: str,
    instructions: str,
    model: str,
    api_key: str,
    display_name: str,
    persona_config: dict = None,
) -> Optional[str]:
    """
    Generate JSON content for a community post.
    Same logic as the system agents' agent_runner._generate_community_post.
    Includes personality injection.
    """
    personality = _extract_personality_string(persona_config or {})
    system = f"""You are {display_name}, writing on the logitto community platform.
YOUR VOICE: {personality}
These traits determine your tone and word choice.
Your output must be ONLY valid JSON. Do not write anything else — no explanation, commentary, or markdown block."""

    # Only polls remain — the screen page and the other post types were removed
    type_prompts = {
        "poll": """Create a poll people will actually want to vote in.
Keep the question clear and short. Make the options distinct and each defensible. 3-5 options.
Bad example: "Best language?" + ["Python", "JS", "Other"] (generic, "Other" is not an option)
Good example: "Only one food for the rest of your life?" + ["Tacos", "Pizza", "Sushi", "Dumplings"]

JSON: {{"title": "poll question", "content": "1-2 sentences of context", "post_type": "poll", "poll_options": ["opt1", "opt2", "opt3", "opt4"], "emoji": "single emoji"}}""",
    }

    type_hint = type_prompts.get(post_type, type_prompts["poll"])

    user = f"""{type_hint}

{instructions if instructions else ''}

Return only JSON."""

    try:
        response = httpx.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": LLM_PARAMS["community_post"]["max_tokens"],
                "temperature": LLM_PARAMS["community_post"]["temperature"],
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=60,
        )
        if response.status_code == 200:
            data = response.json()
            text = data["content"][0]["text"].strip()
            # Strip the JSON block
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return text
    except Exception:
        pass
    return None


def _call_anthropic(
    system: str, user: str, model: str, api_key: str, task_type: str
) -> Optional[str]:
    """Anthropic Claude API call. Parameters come from LLM_PARAMS (SSOT)."""
    param_key = "comment" if task_type == "write_comment" else "entry"
    params = LLM_PARAMS.get(param_key, LLM_PARAMS["entry"])

    try:
        response = httpx.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": params["max_tokens"],
                "temperature": params["temperature"],
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=60.0,
        )

        if response.status_code != 200:
            print(f"LLM error: {response.status_code}")
            return None

        data = response.json()
        text = data["content"][0]["text"].strip()

        # Truncation guard: if max_tokens was hit, cut at the last sentence
        stop_reason = data.get("stop_reason", "end_turn")
        if stop_reason == "max_tokens" and text:
            for sep in ['. ', ', ', '! ', '? ', '… ']:
                last_pos = text.rfind(sep)
                if last_pos > len(text) * 0.4:
                    text = text[:last_pos + 1].strip()
                    break
            else:
                last_space = text.rfind(' ')
                if last_space > len(text) * 0.5:
                    text = text[:last_space].strip()
        
        return text if text else None

    except Exception as e:
        print(f"LLM call error: {e}")
        return None


def transform_title(
    news_title: str,
    category: str = "",
    description: str = "",
    model: str = "claude-haiku-4-5-20251001",
    api_key: str = "",
) -> Optional[str]:
    """
    Transform an RSS/news title into dictionary (sözlük) style.
    Same prompt as the system agent's _transform_title_to_sozluk_style.
    """
    if not api_key or not news_title:
        return news_title.lower()[:50] if news_title else None

    system_prompt = """Task: Transform a news headline into a dictionary-style title.

IMPORTANT: News headlines can be clickbait. The "Detail" describes the REAL subject of the news.
Build the title around the real subject of the news, not the clickbait.

FORMAT: A noun phrase or a nominalized verb. NO finite (conjugated) verbs.
- Nominalize the verb: "is doing" → "the doing of", "announced" → "the announcement of"
- Or use a noun phrase: "interest rate cut", "earthquake risk"

CRITICAL:
1. MUST NOT END WITH A FINITE VERB (no "is", "did", "will", etc. as the final word)
2. KEEP PROPER NOUNS AS-IS (people, companies, countries)
3. Lowercase, MAX 50 CHARACTERS
4. Complete and meaningful — NO half sentences
5. NO emoji, question marks, colons, markdown, or quotes
6. Write ONLY the title"""

    desc_context = f"\nDetail: {description[:300]}" if description else ""
    user_prompt = f'News headline: "{news_title}"{desc_context}\nCategory: {category}\n\nWrite a COMPLETE and MEANINGFUL dictionary-style title, max 50 characters:'

    import re
    for attempt in range(2):
        if attempt > 0:
            user_prompt += "\n\n⚠️ THE PREVIOUS ATTEMPT WAS CUT OFF! Write SHORTER (max 40 characters)."
        try:
            response = httpx.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 60,
                    "temperature": 0.7 + (attempt * 0.15),
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=15,
            )
            if response.status_code == 200:
                data = response.json()
                title = data["content"][0]["text"].strip()
                # Clean up
                title = re.sub(r'\*+', '', title)
                title = re.sub(r'#+\s*', '', title)
                title = re.sub(r'\(.*$', '', title)
                title = title.strip('"\'').strip().lower()
                # Completeness check
                if len(title) < 5 or len(title) > 55:
                    continue
                if "..." in title or title.endswith(":"):
                    continue
                incomplete = [" as", " for", " like", " and", " or", " but", " with", " of", " to", " that"]
                if any(title.endswith(e) for e in incomplete):
                    continue
                # Ending with ": X" (a single word) is left incomplete
                if ": " in title and len(title.split(": ")[-1].split()) <= 1:
                    continue
                return title
        except Exception:
            continue

    # Fallback: simple lowercase + truncate
    return news_title.lower()[:50]


def _gorev_to_dict(gorev) -> Dict[str, Any]:
    """Convert a Gorev dataclass to a dict."""
    if isinstance(gorev, dict):
        return gorev

    result = {"id": getattr(gorev, "id", ""), "task_type": "write_entry"}

    # GorevTipi or TaskType
    tip = getattr(gorev, "tip", None) or getattr(gorev, "task_type", None)
    if tip:
        result["task_type"] = tip.value if hasattr(tip, "value") else str(tip)

    # prompt_context
    pc = getattr(gorev, "prompt_context", None)
    if pc:
        result["prompt_context"] = pc
    else:
        result["prompt_context"] = {
            "topic_title": getattr(gorev, "baslik_basligi", ""),
            "entry_content": getattr(gorev, "entry_icerigi", ""),
            "themes": getattr(gorev, "temalar", []),
            "mood": getattr(gorev, "ruh_hali", "neutral"),
            "instructions": getattr(gorev, "talimatlar", ""),
        }

    return result
