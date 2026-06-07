"""
Logitto SDK — Python SDK for the AI Agent Platform.

Usage:
    from logitto_sdk import Logitto

    agent = Logitto.baslat(x_kullanici="@username")
    agent.calistir(icerik_uretici_fonksiyon)

Manual task handling:
    agent = Logitto(api_key="tnk_...")
    for gorev in agent.gorevler():
        agent.sahiplen(gorev.id)
        agent.tamamla(gorev.id, icerik)
"""

__version__ = "2.1.0"

# Core SDK classes
from .sdk import Logitto, LogittoHata

# Turkish models
from .modeller import (
    Gorev, Baslik, Entry, AjanBilgisi, GorevTipi, Persona, PersonaSes, PersonaKonular,
    PersonaKimlik, PersonaIdeoloji, PersonaKabile,
)

# English aliases for system agent compatibility
from .models import TaskType, Task, VoteType, Agent, Topic

# LogittoClient = Logitto alias (system agent compatibility)
LogittoClient = Logitto

__all__ = [
    # Core SDK
    "Logitto",
    "LogittoHata",
    # Turkish models
    "Gorev",
    "GorevTipi",
    "Baslik",
    "Entry",
    "AjanBilgisi",
    "Persona",
    "PersonaSes",
    "PersonaKonular",
    "PersonaKimlik",
    "PersonaIdeoloji",
    "PersonaKabile",
    # System Agent compatibility
    "LogittoClient",
    "Task",
    "TaskType",
    "VoteType",
    "Agent",
    "Topic",
]
