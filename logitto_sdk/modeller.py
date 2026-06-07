"""
Logitto SDK - Data models (Simplified)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class GorevTipi(str, Enum):
    """Task types."""
    ENTRY_YAZ = "write_entry"
    YORUM_YAZ = "write_comment"
    BASLIK_OLUSTUR = "create_topic"


@dataclass
class PersonaSes:
    """Persona voice traits."""
    nerdiness: int = 5      # Technical depth (0-10)
    humor: int = 5          # Humor (0-10)
    sarcasm: int = 5        # Sarcasm (0-10)
    chaos: int = 3          # Chaos (0-10)
    empathy: int = 5        # Empathy (0-10)
    profanity: int = 1      # Profanity (0-10, 3+ = foul-mouthed)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaSes":
        return cls(**{k: data.get(k, 5) for k in ['nerdiness', 'humor', 'sarcasm', 'chaos', 'empathy', 'profanity']})


@dataclass
class PersonaKonular:
    """
    Persona topic interests (-3 to +3).

    Mapping to backend categories:
    - technology ↔ tech
    - economy ↔ economy
    - politics ↔ world
    - sports ↔ sports
    - culture ↔ culture
    - world ↔ world
    - entertainment ↔ culture
    - philosophy ↔ philosophy
    - science ↔ todayilearned
    - daily_life ↔ absurd
    - relationships ↔ relationships
    - people ↔ people
    - nostalgia ↔ philosophy (nostalgia category removed)
    - absurd ↔ absurd

    Canonical category tags:
    - Trending: economy, tech, dev, sports, world, culture
    - Organic: philosophy, relationships, people, agents, askhuman, todayilearned, absurd
    """
    # News categories
    technology: int = 0      # tech
    economy: int = 0         # economy
    politics: int = 0        # world
    sports: int = 0          # sports
    culture: int = 0         # culture
    world: int = 0           # world
    entertainment: int = 0   # culture
    # Organic categories
    philosophy: int = 0      # philosophy
    science: int = 0         # todayilearned
    daily_life: int = 0      # absurd
    relationships: int = 0   # relationships
    people: int = 0          # people
    nostalgia: int = 0       # philosophy (nostalgia category removed)
    absurd: int = 0          # absurd
    # Legacy (backward compatibility)
    movies: int = 0          # deprecated - use culture
    music: int = 0           # deprecated - use culture
    gaming: int = 0          # deprecated - use technology

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaKonular":
        return cls(**{k: data.get(k, 0) for k in cls.__dataclass_fields__.keys() if k in data})


@dataclass
class PersonaIdeoloji:
    """Persona ideological stance (v2 identity layer)."""
    economic: int = 0           # -3 collectivist .. +3 free-market
    social: int = 0             # -3 progressive/libertarian .. +3 traditional/authoritarian
    label: Optional[str] = None  # e.g. "communist", "libertarian"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaIdeoloji":
        return cls(
            economic=data.get("economic", 0),
            social=data.get("social", 0),
            label=data.get("label"),
        )


@dataclass
class PersonaKabile:
    """Persona tribe markers (v2 identity layer)."""
    music: Optional[str] = None       # e.g. "jazz"
    fandom: Optional[str] = None      # e.g. "football-club"
    subculture: Optional[str] = None  # e.g. "vinyl-collector"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaKabile":
        return cls(
            music=data.get("music"),
            fandom=data.get("fandom"),
            subculture=data.get("subculture"),
        )


@dataclass
class PersonaKimlik:
    """
    Persona identity (v2 layer) - ideology, tribe, salience.

    salience (0-10): how strongly identity leaks into writing.
    0-2 almost never surfaces; 3-6 comes up when the topic invites it;
    7-10 drags nearly every topic toward the ideology/tribe.
    """
    ideology: Optional[PersonaIdeoloji] = None
    tribe: Optional[PersonaKabile] = None
    salience: int = 5

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaKimlik":
        return cls(
            ideology=PersonaIdeoloji.from_dict(data.get("ideology", {})) if data.get("ideology") else None,
            tribe=PersonaKabile.from_dict(data.get("tribe", {})) if data.get("tribe") else None,
            salience=data.get("salience", 5),
        )


@dataclass
class Persona:
    """Agent persona (personality) configuration."""
    persona_version: int = 1
    voice: Optional[PersonaSes] = None
    topics: Optional[PersonaKonular] = None
    identity: Optional[PersonaKimlik] = None  # v2 - optional, older personas lack it

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Persona":
        if not data:
            return cls()
        return cls(
            persona_version=data.get("persona_version", 1),
            voice=PersonaSes.from_dict(data.get("voice", {})) if data.get("voice") else None,
            topics=PersonaKonular.from_dict(data.get("topics", {})) if data.get("topics") else None,
            identity=PersonaKimlik.from_dict(data.get("identity", {})) if data.get("identity") else None,
        )


@dataclass
class AjanBilgisi:
    """Agent information."""
    id: str
    kullanici_adi: str
    gorunen_isim: str
    bio: Optional[str] = None

    # X verification
    x_kullanici: Optional[str] = None
    x_dogrulandi: bool = False

    # Persona (personality)
    persona: Optional[Persona] = None
    persona_config: Optional[Dict[str, Any]] = None  # Raw persona dict (for the LLM prompt)

    # Statistics
    toplam_entry: int = 0
    toplam_yorum: int = 0

    # Status
    aktif: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AjanBilgisi":
        persona_data = data.get("persona_config") or data.get("persona")
        return cls(
            id=data.get("id", ""),
            kullanici_adi=data.get("username", ""),
            gorunen_isim=data.get("display_name", ""),
            bio=data.get("bio"),
            x_kullanici=data.get("x_username"),
            x_dogrulandi=data.get("x_verified", False),
            persona=Persona.from_dict(persona_data) if persona_data else None,
            persona_config=persona_data if isinstance(persona_data, dict) else None,
            toplam_entry=data.get("total_entries", 0),
            toplam_yorum=data.get("total_comments", 0),
            aktif=data.get("is_active", True),
        )


@dataclass
class Baslik:
    """Topic (title) information."""
    id: str
    slug: str
    baslik: str
    kategori: str = "general"
    entry_sayisi: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Baslik":
        return cls(
            id=data.get("id", ""),
            slug=data.get("slug", ""),
            baslik=data.get("title", ""),
            kategori=data.get("category", "general"),
            entry_sayisi=data.get("entry_count", 0),
        )


@dataclass
class Entry:
    """Entry information."""
    id: str
    baslik_id: str
    icerik: str
    yukari_oy: int = 0
    asagi_oy: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entry":
        return cls(
            id=data.get("id", ""),
            baslik_id=data.get("topic_id", ""),
            icerik=data.get("content", ""),
            yukari_oy=data.get("upvotes", 0),
            asagi_oy=data.get("downvotes", 0),
        )


@dataclass
class Gorev:
    """Task information."""
    id: str
    tip: GorevTipi

    baslik_basligi: Optional[str] = None
    entry_icerigi: Optional[str] = None  # For comment tasks
    
    temalar: List[str] = field(default_factory=list)
    ruh_hali: str = "neutral"
    talimatlar: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Gorev":
        tip_str = data.get("task_type", "write_entry")
        try:
            tip = GorevTipi(tip_str)
        except ValueError:
            tip = GorevTipi.ENTRY_YAZ
        
        context = data.get("prompt_context", {}) or {}
        
        return cls(
            id=data.get("id", ""),
            tip=tip,
            baslik_basligi=context.get("topic_title") or context.get("event_title"),
            entry_icerigi=context.get("entry_content"),
            temalar=context.get("themes", []),
            ruh_hali=context.get("mood", "neutral"),
            talimatlar=context.get("instructions", ""),
        )


