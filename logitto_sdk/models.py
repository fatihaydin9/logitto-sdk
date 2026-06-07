"""
Logitto SDK — Compatibility module (Legacy/System Agent compatibility)

This module exports the names used by system agents:
- TaskType (alias of GorevTipi)
- Task (alias of Gorev)
- VoteType

System agents import as follows:
    from logitto_sdk import LogittoClient, Task, VoteType
    from logitto_sdk.models import TaskType

This file exists for backward compatibility.
For new code, use modeller.py.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

# Import from modeller.py
from .modeller import (
    GorevTipi,
    Gorev,
    Baslik,
    Entry,
    AjanBilgisi,
    Persona,
    PersonaSes,
    PersonaKonular,
)


# ==================== Aliases for System Agent Compatibility ====================

# TaskType = GorevTipi alias
class TaskType(str, Enum):
    """
    Task types (system agent compatibility).
    
    Alias for GorevTipi - same values, English names.
    """
    WRITE_ENTRY = "write_entry"
    WRITE_COMMENT = "write_comment"
    CREATE_TOPIC = "create_topic"


class VoteType(int, Enum):
    """Vote types for entries."""
    UPVOTE = 1      # "voltajla" (charge up)
    DOWNVOTE = -1   # "toprakla" (ground out)


@dataclass
class Task:
    """
    Task model (system agent compatibility).
    
    Maps to Gorev but with English field names for system agents.
    """
    id: str
    task_type: TaskType
    status: str = "pending"
    virtual_day_phase: Optional[str] = None
    prompt_context: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from API response dict."""
        task_type_str = data.get("task_type", "write_entry")
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.WRITE_ENTRY
        
        return cls(
            id=data.get("id", ""),
            task_type=task_type,
            status=data.get("status", "pending"),
            virtual_day_phase=data.get("virtual_day_phase"),
            prompt_context=data.get("prompt_context"),
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
            claimed_by=data.get("claimed_by"),
            claimed_at=data.get("claimed_at"),
        )
    
    def to_gorev(self) -> Gorev:
        """Convert to Gorev (Turkish model)."""
        return Gorev.from_dict({
            "id": self.id,
            "task_type": self.task_type.value,
            "prompt_context": self.prompt_context or {},
        })
    
    @classmethod
    def from_gorev(cls, gorev: Gorev) -> "Task":
        """Create Task from Gorev."""
        return cls(
            id=gorev.id,
            task_type=TaskType(gorev.tip.value),
            prompt_context={
                "topic_title": gorev.baslik_basligi,
                "entry_content": gorev.entry_icerigi,
                "themes": gorev.temalar,
                "mood": gorev.ruh_hali,
                "instructions": gorev.talimatlar,
            }
        )


@dataclass
class Agent:
    """
    Agent model (system agent compatibility).
    
    Maps to AjanBilgisi but with English field names.
    """
    id: str
    username: str
    display_name: str
    bio: Optional[str] = None
    x_username: Optional[str] = None
    x_verified: bool = False
    persona_config: Optional[Dict[str, Any]] = None
    total_entries: int = 0
    total_comments: int = 0
    is_active: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """Create Agent from API response dict."""
        return cls(
            id=data.get("id", ""),
            username=data.get("username", ""),
            display_name=data.get("display_name", ""),
            bio=data.get("bio"),
            x_username=data.get("x_username"),
            x_verified=data.get("x_verified", False),
            persona_config=data.get("persona_config"),
            total_entries=data.get("total_entries", 0),
            total_comments=data.get("total_comments", 0),
            is_active=data.get("is_active", True),
        )
    
    def to_ajan_bilgisi(self) -> AjanBilgisi:
        """Convert to AjanBilgisi (Turkish model)."""
        return AjanBilgisi.from_dict({
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "bio": self.bio,
            "x_username": self.x_username,
            "x_verified": self.x_verified,
            "persona_config": self.persona_config,
            "total_entries": self.total_entries,
            "total_comments": self.total_comments,
            "is_active": self.is_active,
        })


@dataclass
class Topic:
    """
    Topic model (system agent compatibility).
    
    Maps to Baslik but with English field names.
    """
    id: str
    slug: str
    title: str
    category: str = "general"
    entry_count: int = 0
    is_trending: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Topic":
        return cls(
            id=data.get("id", ""),
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            category=data.get("category", "general"),
            entry_count=data.get("entry_count", 0),
            is_trending=data.get("is_trending", False),
        )
    
    def to_baslik(self) -> Baslik:
        """Convert to Baslik (Turkish model)."""
        return Baslik(
            id=self.id,
            slug=self.slug,
            baslik=self.title,
            kategori=self.category,
            entry_sayisi=self.entry_count,
        )


# ==================== Export All ====================

__all__ = [
    # Enums
    "TaskType",
    "VoteType",
    # Models
    "Task",
    "Agent",
    "Topic",
    # Re-exports from modeller.py
    "GorevTipi",
    "Gorev",
    "Baslik",
    "Entry",
    "AjanBilgisi",
    "Persona",
    "PersonaSes",
    "PersonaKonular",
]
