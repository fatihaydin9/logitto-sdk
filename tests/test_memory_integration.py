"""
Memory System Integration Tests - Verifies the consistency of the agent memory system.

Tested:
1. 3-Layer Memory Architecture (Episodic, Semantic, Character)
2. Memory Decay System (Short-term fade, Long-term promotion)
3. Garbage Collection (MAX_EPISODIC, MAX_SEMANTIC limits)
4. Persistence (JSON file storage)
5. Access counting and auto-promotion

No mocks - real AgentMemory instances are used.
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import fields, asdict

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
AGENTS_PATH = PROJECT_ROOT / "agents"

if str(AGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(AGENTS_PATH))

from agent_memory import (
    AgentMemory,
    EpisodicEvent,
    SemanticFact,
    CharacterSheet,
    SocialFeedback,
    generate_social_feedback,
    SHORT_TERM_DECAY_DAYS,
    LONG_TERM_THRESHOLD,
)


@pytest.fixture
def temp_memory_dir():
    """Create a temporary memory directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory(temp_memory_dir):
    """An AgentMemory instance for testing."""
    return AgentMemory("testagent", memory_dir=str(temp_memory_dir))


# ============ 3-Layer Architecture Tests ============

class TestThreeLayerArchitecture:
    """3-layer memory architecture tests."""

    def test_memory_has_three_layers(self, memory):
        """Memory should have 3 layers."""
        assert hasattr(memory, 'episodic')
        assert hasattr(memory, 'semantic')
        assert hasattr(memory, 'character')

    def test_episodic_layer_is_list(self, memory):
        """The episodic layer should be a list of EpisodicEvent."""
        assert isinstance(memory.episodic, list)

    def test_semantic_layer_is_list(self, memory):
        """The semantic layer should be a list of SemanticFact."""
        assert isinstance(memory.semantic, list)

    def test_character_layer_is_sheet(self, memory):
        """The character layer should be a CharacterSheet."""
        assert isinstance(memory.character, CharacterSheet)


# ============ Episodic Memory Tests ============

class TestEpisodicMemory:
    """Episodic (raw event) memory tests."""

    def test_add_entry_creates_event(self, memory):
        """Adding an entry should create an episodic event."""
        memory.add_entry(
            content="Test entry content",
            topic_title="Test Title",
            topic_id="topic-123",
            entry_id="entry-456"
        )

        assert len(memory.episodic) == 1
        assert memory.episodic[0].event_type == 'wrote_entry'
        assert memory.episodic[0].topic_title == "Test Title"

    def test_add_comment_creates_event(self, memory):
        """Adding a comment should create an episodic event."""
        memory.add_comment(
            content="Test comment",
            topic_title="Test Title",
            topic_id="topic-123",
            entry_id="entry-456"
        )

        assert len(memory.episodic) == 1
        assert memory.episodic[0].event_type == 'wrote_comment'

    def test_event_has_timestamp(self, memory):
        """An event should have a timestamp."""
        memory.add_entry("content", "title", "tid", "eid")

        event = memory.episodic[0]
        assert event.timestamp is not None
        # Should be ISO format
        datetime.fromisoformat(event.timestamp)

    def test_event_has_unique_id(self, memory):
        """Each event should have a unique ID."""
        memory.add_entry("content1", "title1", "tid1", "eid1")
        memory.add_entry("content2", "title2", "tid2", "eid2")

        ids = [e.id for e in memory.episodic]
        assert len(ids) == len(set(ids))  # All unique

    def test_event_to_narrative(self, memory):
        """An event should be convertible to narrative format."""
        memory.add_entry("test content", "Test Topic", "tid", "eid")

        event = memory.episodic[0]
        narrative = event.to_narrative()

        assert "Test Topic" in narrative
        assert "I wrote an entry about" in narrative


# ============ Semantic Memory Tests ============

class TestSemanticMemory:
    """Semantic (derived knowledge) memory tests."""

    def test_semantic_fact_structure(self):
        """SemanticFact should have the correct structure."""
        fact = SemanticFact(
            fact_type="preference",
            subject="testagent",
            predicate="likes technology topics"
        )

        assert fact.fact_type == "preference"
        assert fact.subject == "testagent"
        assert fact.confidence == 0.5  # default

    def test_fact_to_statement(self):
        """A fact should be expressible as a statement."""
        fact = SemanticFact(
            fact_type="preference",
            subject="Agent",
            predicate="likes humor",
            confidence=0.9
        )

        statement = fact.to_statement()
        assert "Agent" in statement
        assert "likes humor" in statement

    def test_add_semantic_fact(self, memory):
        """A semantic fact should be addable."""
        fact = SemanticFact(
            fact_type="topic_affinity",
            subject="testagent",
            predicate="interested in technology topics"
        )
        memory.semantic.append(fact)
        memory._save()

        assert len(memory.semantic) == 1


# ============ Character Sheet Tests ============

class TestCharacterSheet:
    """Character sheet tests."""

    def test_character_sheet_defaults(self):
        """CharacterSheet should have default values."""
        char = CharacterSheet()

        assert char.message_length == "medium"
        assert char.tone == "neutral"
        assert char.uses_slang == False
        assert char.uses_emoji == False

    def test_character_sheet_to_prompt(self):
        """CharacterSheet should be convertible to a prompt."""
        char = CharacterSheet(
            tone="sarcastic",
            favorite_topics=["technology", "philosophy"],
            humor_style="dry"
        )

        prompt = char.to_prompt_section()

        assert "sarcastic" in prompt
        assert "technology" in prompt
        assert "dry" in prompt

    def test_karma_awareness(self):
        """CharacterSheet should have karma awareness."""
        char = CharacterSheet(karma_score=5.0, karma_trend="rising")

        assert char.karma_score == 5.0
        assert char.karma_trend == "rising"

        # Karma reaction
        reaction = char.get_karma_reaction()
        assert reaction == "proud"


# ============ Memory Decay Tests ============

class TestMemoryDecay:
    """Memory decay tests."""

    def test_decay_constants_exist(self):
        """The decay constants should be defined."""
        assert SHORT_TERM_DECAY_DAYS == 14
        assert LONG_TERM_THRESHOLD == 3

    def test_fresh_memory_survives_decay(self, memory):
        """Fresh memory should survive decay."""
        memory.add_entry("fresh content", "Fresh Topic", "tid", "eid")

        memory.apply_decay()

        assert len(memory.episodic) == 1

    def test_old_memory_decays(self, memory):
        """Old memory should decay."""
        # Create an old event (15 days ago)
        old_event = EpisodicEvent(
            event_type='wrote_entry',
            content='old content',
            topic_title='Old Topic',
            timestamp=(datetime.now() - timedelta(days=15)).isoformat()
        )
        memory.episodic.append(old_event)

        memory.apply_decay()

        assert len(memory.episodic) == 0

    def test_long_term_memory_survives_decay(self, memory):
        """Long-term memory should not be affected by decay."""
        # Old but long-term event
        old_event = EpisodicEvent(
            event_type='wrote_entry',
            content='important content',
            topic_title='Important Topic',
            timestamp=(datetime.now() - timedelta(days=30)).isoformat(),
            is_long_term=True
        )
        memory.episodic.append(old_event)

        memory.apply_decay()

        assert len(memory.episodic) == 1
        assert memory.episodic[0].is_long_term == True

    def test_frequently_accessed_survives(self, memory):
        """Frequently accessed memory should survive decay."""
        # Old but frequently accessed event
        old_event = EpisodicEvent(
            event_type='wrote_entry',
            content='popular content',
            topic_title='Popular Topic',
            timestamp=(datetime.now() - timedelta(days=20)).isoformat(),
            access_count=LONG_TERM_THRESHOLD  # 3+ accesses
        )
        memory.episodic.append(old_event)

        memory.apply_decay()

        # Should be auto-promoted to long-term
        assert len(memory.episodic) == 1
        assert memory.episodic[0].is_long_term == True


# ============ Long-Term Promotion Tests ============

class TestLongTermPromotion:
    """Long-term memory promotion tests."""

    def test_manual_promotion(self, memory):
        """Manual promotion should work."""
        memory.add_entry("content", "title", "tid", "eid")
        event_id = memory.episodic[0].id

        result = memory.promote_to_long_term(event_id)

        assert result == True
        assert memory.episodic[0].is_long_term == True

    def test_auto_promotion_on_access(self, memory):
        """Frequent access should trigger auto-promotion."""
        memory.add_entry("content", "title", "tid", "eid")
        event_id = memory.episodic[0].id

        # Access LONG_TERM_THRESHOLD times
        for _ in range(LONG_TERM_THRESHOLD):
            memory.access_event(event_id)

        assert memory.episodic[0].is_long_term == True

    def test_access_count_increments(self, memory):
        """The access count should increment."""
        memory.add_entry("content", "title", "tid", "eid")
        event_id = memory.episodic[0].id

        assert memory.episodic[0].access_count == 0

        memory.access_event(event_id)
        assert memory.episodic[0].access_count == 1

        memory.access_event(event_id)
        assert memory.episodic[0].access_count == 2

    def test_get_long_term_memories(self, memory):
        """Long-term memories should be filterable."""
        # Normal event
        memory.add_entry("normal", "Normal", "tid1", "eid1")

        # Long-term event
        memory.add_entry("important", "Important", "tid2", "eid2")
        memory.promote_to_long_term(memory.episodic[1].id)

        long_term = memory.get_long_term_memories()

        assert len(long_term) == 1
        assert long_term[0].topic_title == "Important"


# ============ Garbage Collection Tests ============

class TestGarbageCollection:
    """Garbage collection (memory limit) tests."""

    def test_max_episodic_limit(self, memory):
        """Episodic memory should be capped by MAX_EPISODIC."""
        assert hasattr(memory, 'MAX_EPISODIC')
        assert memory.MAX_EPISODIC == 200

    def test_max_semantic_limit(self, memory):
        """Semantic memory should be capped by MAX_SEMANTIC."""
        assert hasattr(memory, 'MAX_SEMANTIC')
        assert memory.MAX_SEMANTIC == 50

    def test_episodic_trimmed_on_save(self, memory):
        """Episodic memory should be trimmed on save."""
        # Add more events than MAX_EPISODIC
        for i in range(memory.MAX_EPISODIC + 50):
            memory.episodic.append(EpisodicEvent(
                event_type='wrote_entry',
                content=f'content_{i}',
                topic_title=f'Topic_{i}'
            ))

        memory._save()

        # Reload the file
        memory2 = AgentMemory("testagent", memory_dir=str(memory.memory_dir))

        # Only the last MAX_EPISODIC should be kept
        assert len(memory2.episodic) == memory.MAX_EPISODIC


# ============ Persistence Tests ============

class TestPersistence:
    """Memory persistence tests."""

    def test_episodic_saved_to_file(self, memory):
        """Episodic memory should be saved to a file."""
        memory.add_entry("content", "title", "tid", "eid")

        assert memory.episodic_file.exists()

    def test_semantic_saved_to_file(self, memory):
        """Semantic memory should be saved to a file."""
        fact = SemanticFact("preference", "agent", "test")
        memory.semantic.append(fact)
        memory._save()

        assert memory.semantic_file.exists()

    def test_character_saved_to_file(self, memory):
        """The character sheet should be saved to a file."""
        memory.character.tone = "sarcastic"
        memory._save()

        assert memory.character_file.exists()

    def test_memory_persists_across_instances(self, temp_memory_dir):
        """Memory should persist across instances."""
        # First instance
        mem1 = AgentMemory("testagent", memory_dir=str(temp_memory_dir))
        mem1.add_entry("persistent content", "Persistent Topic", "tid", "eid")

        # Second instance (same directory)
        mem2 = AgentMemory("testagent", memory_dir=str(temp_memory_dir))

        assert len(mem2.episodic) == 1
        assert mem2.episodic[0].topic_title == "Persistent Topic"

    def test_long_term_saved_to_markdown(self, memory):
        """Long-term memory should be saved to a markdown file."""
        memory.add_entry("important content", "Important Topic", "tid", "eid")
        event_id = memory.episodic[0].id
        
        memory.promote_to_long_term(event_id)
        
        long_term_dir = memory.memory_dir / "long_term"
        md_file = long_term_dir / f"{event_id}.md"
        
        assert md_file.exists()
        
        content = md_file.read_text(encoding='utf-8')
        assert "wrote_entry" in content
        assert "Important Topic" in content


# ============ Social Feedback Tests ============

class TestSocialFeedback:
    """Social feedback tests."""

    def test_social_feedback_structure(self):
        """SocialFeedback should have the correct structure."""
        feedback = SocialFeedback(likes=5, dislikes=1, replies=2)

        assert feedback.likes == 5
        assert feedback.dislikes == 1
        assert feedback.replies == 2

    def test_is_positive(self):
        """Positive feedback should be detected correctly."""
        positive = SocialFeedback(likes=10, dislikes=2)
        negative = SocialFeedback(likes=1, dislikes=5)

        assert positive.is_positive() == True
        assert negative.is_positive() == False

    def test_feedback_summary(self):
        """A feedback summary should be generated."""
        feedback = SocialFeedback(likes=5, dislikes=1, criticism="too long")
        summary = feedback.summary()

        assert "+5" in summary
        assert "-1" in summary
        assert "criticism" in summary

    def test_add_received_feedback(self, memory):
        """Received feedback should be recordable."""
        feedback = SocialFeedback(likes=3, replies=1)
        memory.add_received_feedback(feedback, "entry-123", "Test Topic")

        assert memory.stats['total_likes_received'] == 3


# ============ Relationship Decay Tests ============

class TestRelationshipDecay:
    """Relationship decay tests."""

    def test_decay_relationships_exists(self, memory):
        """The decay_relationships method should exist."""
        assert hasattr(memory, 'decay_relationships')

    def test_relationship_confidence_decays(self, memory):
        """The confidence of inactive relationships should decay."""
        # Add an old relationship fact
        old_fact = SemanticFact(
            fact_type='relationship',
            subject='other_agent',
            predicate='is a friend',
            confidence=0.9,
            last_updated=(datetime.now() - timedelta(hours=200)).isoformat()
        )
        memory.semantic.append(old_fact)

        memory.decay_relationships(hours=168)  # 1 week

        # Confidence should decay toward 0.5
        assert memory.semantic[0].confidence < 0.9


# ============ Stats Tests ============

class TestStats:
    """Statistics tests."""

    def test_stats_initialized(self, memory):
        """Stats should be zero initially."""
        assert memory.stats['total_entries'] == 0
        assert memory.stats['total_comments'] == 0
        assert memory.stats['total_votes'] == 0

    def test_entry_increments_stats(self, memory):
        """Adding an entry should increment the stats."""
        memory.add_entry("content", "title", "tid", "eid")

        assert memory.stats['total_entries'] == 1

    def test_comment_increments_stats(self, memory):
        """Adding a comment should increment the stats."""
        memory.add_comment("content", "title", "tid", "eid")

        assert memory.stats['total_comments'] == 1

    def test_stats_persisted(self, temp_memory_dir):
        """Stats should persist."""
        mem1 = AgentMemory("testagent", memory_dir=str(temp_memory_dir))
        mem1.add_entry("content", "title", "tid", "eid")
        mem1.add_entry("content2", "title2", "tid2", "eid2")

        mem2 = AgentMemory("testagent", memory_dir=str(temp_memory_dir))

        assert mem2.stats['total_entries'] == 2


# ============ Reflection Tests ============

class TestReflection:
    """Reflection (self-evaluation) tests."""

    def test_reflection_interval_defined(self, memory):
        """The reflection interval should be defined."""
        assert hasattr(memory, 'REFLECTION_INTERVAL')
        assert memory.REFLECTION_INTERVAL == 10  # instructionset.md: every 10 events

    def test_needs_reflection_after_interval(self, memory):
        """Reflection should be needed after the interval."""
        # Add REFLECTION_INTERVAL events
        for i in range(memory.REFLECTION_INTERVAL):
            memory.add_entry(f"content_{i}", f"title_{i}", f"tid_{i}", f"eid_{i}")

        assert memory.needs_reflection() == True

    def test_no_reflection_before_interval(self, memory):
        """Reflection should not be needed before the interval."""
        memory.add_entry("content", "title", "tid", "eid")

        assert memory.needs_reflection() == False
