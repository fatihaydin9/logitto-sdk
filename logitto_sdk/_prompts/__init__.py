"""
Vendored shared_prompts — Single Source of Truth

This package is a vendored copy of the shared_prompts/ modules for the SDK.
Source: /shared_prompts/

SYNC: When shared_prompts/ changes, these files must be updated too.
"""

from .system_prompt_builder import (
    SystemPromptBuilder,
    build_system_prompt,
    build_entry_system_prompt,
    build_comment_system_prompt,
    get_dynamic_digital_context,
)

from .prompt_builder import (
    build_entry_prompt,
    build_comment_prompt,
    build_minimal_comment_prompt,
    get_random_mood,
    get_random_opening,
)

from .core_rules import (
    build_dynamic_rules_block,
    DIGITAL_CONTEXT,
    STYLE_RULES,
    GOOD_EXAMPLES,
)

__all__ = [
    "SystemPromptBuilder",
    "build_system_prompt",
    "build_entry_system_prompt",
    "build_comment_system_prompt",
    "get_dynamic_digital_context",
    "build_entry_prompt",
    "build_comment_prompt",
    "build_minimal_comment_prompt",
    "get_random_mood",
    "get_random_opening",
    "build_dynamic_rules_block",
    "DIGITAL_CONTEXT",
    "STYLE_RULES",
    "GOOD_EXAMPLES",
]
