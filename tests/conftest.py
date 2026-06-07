"""
Pytest configuration and fixtures for SDK tests.
"""

import pytest
import sys
from pathlib import Path

# Set up project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SDK_PATH = PROJECT_ROOT / "sdk" / "python"
AGENTS_PATH = PROJECT_ROOT / "agents"
SKILLS_PATH = PROJECT_ROOT / "skills"

# Add the paths to sys.path
sys.path.insert(0, str(SDK_PATH))
sys.path.insert(0, str(AGENTS_PATH))


@pytest.fixture(scope="session")
def project_root():
    """The project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def skills_dir():
    """The skills/ directory."""
    return SKILLS_PATH


@pytest.fixture(scope="session")
def sdk_dir():
    """The SDK directory."""
    return SDK_PATH


@pytest.fixture(scope="session")
def agents_dir():
    """The agents/ directory."""
    return AGENTS_PATH


@pytest.fixture
def reset_skills_loader():
    """Reset the SkillsLoader singleton."""
    from skills_loader import SkillsLoader
    SkillsLoader._instance = None
    yield
    SkillsLoader._instance = None


@pytest.fixture
def sample_persona_data():
    """Sample persona data."""
    return {
        "persona_version": 1,
        "voice": {
            "nerdiness": 7,
            "humor": 5,
            "sarcasm": 8,
            "chaos": 3,
            "empathy": 4,
            "profanity": 1
        },
        "topics": {
            "technology": 3,
            "economy": 1,
            "politics": -2,
            "sports": -1,
            "philosophy": 2
        }
    }


@pytest.fixture
def sample_task_data():
    """Sample task data."""
    return {
        "id": "task-uuid-123",
        "task_type": "write_entry",
        "prompt_context": {
            "topic_title": "will ai take over jobs in the future",
            "themes": ["technology", "philosophy"],
            "mood": "curious",
            "instructions": "Write based on your own experience"
        }
    }


@pytest.fixture
def sample_agent_data(sample_persona_data):
    """Sample agent data."""
    return {
        "id": "agent-uuid-456",
        "username": "testagent",
        "display_name": "Test Agent",
        "bio": "I am a test agent",
        "x_username": "testagent",
        "x_verified": True,
        "total_entries": 42,
        "total_comments": 15,
        "is_active": True,
        "persona_config": sample_persona_data
    }
