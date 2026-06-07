"""
Prompt Security — SDK vendored version (standalone fallbacks).

Kaynak: shared_prompts/prompt_security.py
"""


def escape_for_prompt(s: str) -> str:
    """Escape special characters for prompt injection prevention."""
    return str(s).replace("{", "{{").replace("}", "}}")


def sanitize(s: str, config_name: str = "default") -> str:
    """Sanitize input string."""
    return str(s)[:500]


def sanitize_multiline(s: str, config_name: str = "default") -> str:
    """Sanitize multiline input string."""
    return str(s)[:2000]


SANITIZE_CONFIGS = {}

__all__ = [
    "sanitize",
    "sanitize_multiline",
    "escape_for_prompt",
    "SANITIZE_CONFIGS",
]
