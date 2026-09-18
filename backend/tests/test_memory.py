import os
import pytest
from backend.memory.engine import ChronosMemoryEngine
from backend.memory.models import ChatRequest, MemoryStatus, MemoryType

import uuid

@pytest.fixture
def engine():
    test_db = os.path.join(os.path.dirname(__file__), f"test_chronos_{uuid.uuid4().hex[:8]}.db")
    eng = ChronosMemoryEngine(db_path=test_db)
    yield eng
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception:
        pass

def test_cross_session_persistence(engine):
    db_file = engine.store.db_path
    # Session 1
    req1 = ChatRequest(user_id="user_test", session_id="s1", message="I live in San Francisco.")
    resp1 = engine.process_chat(req1)
    assert len(resp1.new_memories_extracted) > 0

    # Simulate full engine restart (reopening app)
    new_instance = ChronosMemoryEngine(db_path=db_file)
    memories = new_instance.store.get_user_memories("user_test")
    assert len(memories) >= 1
    assert "San Francisco" in memories[0].content

def test_contradiction_resolution(engine):
    # Day 1: Stated Seattle
    r1 = engine.process_chat(ChatRequest(
        user_id="riku",
        session_id="s_day1",
        message="I live in Seattle.",
        simulated_date="2026-09-01T10:00:00Z"
    ))
    
    active_mems = engine.store.get_user_memories("riku", include_superseded=False)
    assert any("Seattle" in m.content for m in active_mems)

    # Day 3: Stated moved to Tokyo
    r2 = engine.process_chat(ChatRequest(
        user_id="riku",
        session_id="s_day3",
        message="I moved to Tokyo last week.",
        simulated_date="2026-09-03T10:00:00Z"
    ))

    # Verify conflict resolution notes
    assert len(r2.conflict_resolution_notes) > 0
    assert any("Tokyo" in n for n in r2.conflict_resolution_notes)

    # Verify active state
    current_active = engine.store.get_user_memories("riku", include_superseded=False)
    assert any("Tokyo" in m.content for m in current_active)
    assert not any("Seattle" in m.content for m in current_active)

    # Verify historical superseded record
    all_mems = engine.store.get_user_memories("riku", include_superseded=True)
    seattle_mems = [m for m in all_mems if "Seattle" in m.content]
    assert len(seattle_mems) == 1
    assert seattle_mems[0].status == MemoryStatus.SUPERSEDED
    assert seattle_mems[0].superseded_by_id is not None

    # Query where user lives
    q_resp = engine.process_chat(ChatRequest(user_id="riku", message="Where do I live?"))
    assert "Tokyo" in q_resp.answer
    assert any("Tokyo" in a.content and a.is_active for a in q_resp.used_memories)
    assert any("Seattle" in a.content and not a.is_active for a in q_resp.superseded_memories)

def test_multi_user_privacy_isolation(engine):
    # Riku declares confidential project
    engine.process_chat(ChatRequest(user_id="riku", message="My secret project is named Project-Chronos."))
    
    # Vansh asks about secret project
    vansh_resp = engine.process_chat(ChatRequest(user_id="vansh", message="What is my secret project?"))
    assert "Project-Chronos" not in vansh_resp.answer
    assert len(vansh_resp.used_memories) == 0

def test_selective_forgetting_gdpr(engine):
    # User provides phone number
    engine.process_chat(ChatRequest(user_id="riku", message="My phone number is +1-555-0199."))
    
    # Verify memory exists
    mems = engine.store.get_user_memories("riku", include_superseded=False)
    assert any("555-0199" in m.content for m in mems)

    # User issues targeted forget command
    forget_resp = engine.process_chat(ChatRequest(user_id="riku", message="Forget my phone number."))
    assert "purged" in forget_resp.answer.lower()

    # Verify memory is wiped
    mems_after = engine.store.get_user_memories("riku", include_superseded=False, include_forgotten=False)
    assert not any("555-0199" in m.content for m in mems_after)

def test_knowledge_graph_structure(engine):
    engine.process_chat(ChatRequest(user_id="riku", message="I live in Seattle."))
    engine.process_chat(ChatRequest(user_id="riku", message="I moved to Tokyo."))
    
    graph = engine.get_knowledge_graph("riku")
    assert "nodes" in graph and "edges" in graph
    assert len(graph["nodes"]) >= 3 # User + 2 memory nodes
    # Check for evolution edge
    evolution_edges = [e for e in graph["edges"] if e.get("status") == "EVOLUTION"]
    assert len(evolution_edges) >= 1
def test_current_memory_beats_superseded_memory(engine):
    """
    The latest active fact must outrank an older superseded
    fact even when the older fact has strong semantic similarity.
    """

    # Day 1
    engine.process_chat(
        ChatRequest(
            user_id="riku",
            session_id="day1",
            message="I live in Seattle.",
            simulated_date="2026-09-01T10:00:00Z"
        )
    )

    # Day 3
    engine.process_chat(
        ChatRequest(
            user_id="riku",
            session_id="day3",
            message="I moved to Tokyo.",
            simulated_date="2026-09-03T10:00:00Z"
        )
    )

    # Ask current-state question
    response = engine.process_chat(
        ChatRequest(
            user_id="riku",
            session_id="day4",
            message="Where do I currently live?"
        )
    )

    # Current answer must contain Tokyo.
    assert "Tokyo" in response.answer

    # Tokyo must be an active memory.
    assert any(
        "Tokyo" in memory.content
        and memory.is_active
        for memory in response.used_memories
    )

    # Seattle must NOT be treated as current truth.
    assert not any(
        "Seattle" in memory.content
        and memory.is_active
        for memory in response.used_memories
    )

def test_active_memory_beats_superseded_memory_in_retrieval(engine):
    # Day 1: old location
    engine.process_chat(ChatRequest(
        user_id="retrieval_test",
        session_id="day1",
        message="I live in Seattle.",
        simulated_date="2026-09-01T10:00:00Z"
    ))

    # Day 3: new location
    engine.process_chat(ChatRequest(
        user_id="retrieval_test",
        session_id="day3",
        message="I moved to Tokyo.",
        simulated_date="2026-09-03T10:00:00Z"
    ))

    # Search for the current location.
    results = engine.store.vector_search(
        user_id="retrieval_test",
        query="Where do I live?",
        top_k=5,
        min_similarity=0.15
    )

    assert len(results) >= 2

    # The highest-ranked result should be the current memory.
    top_memory = results[0][0]

    assert top_memory.status == MemoryStatus.ACTIVE
    assert "Tokyo" in top_memory.content

def test_historical_query_retrieves_superseded_memory(engine):
    engine.process_chat(ChatRequest(
        user_id="history_test",
        session_id="day1",
        message="I live in Seattle.",
        simulated_date="2026-09-01T10:00:00Z"
    ))

    engine.process_chat(ChatRequest(
        user_id="history_test",
        session_id="day3",
        message="I moved to Tokyo.",
        simulated_date="2026-09-03T10:00:00Z"
    ))

    results = engine.store.vector_search(
        user_id="history_test",
        query="Where did I live before Tokyo?",
        top_k=5,
        min_similarity=0.15
    )

    assert len(results) >= 1

    historical = [
        memory for memory, score in results
        if "Seattle" in memory.content
    ]

    assert len(historical) >= 1

def test_forget_command_removes_memory_completely(engine):
    # Add memory
    r = engine.process_chat(ChatRequest(
        user_id="forget_test",
        session_id="add",
        message="I have a dog named Fido.",
        simulated_date="2026-09-01T10:00:00Z"
    ))

    mem_id = r.new_memories_extracted[0].id

    # Verify exists
    mem_before = engine.store.get_memory_by_id(mem_id)
    assert mem_before is not None

    # Forget it
    engine.process_chat(ChatRequest(
        user_id="forget_test",
        session_id="forget",
        message="Forget my dog Fido.",
        simulated_date="2026-09-02T10:00:00Z"
    ))

    # Verify completely gone
    mem_after = engine.store.get_memory_by_id(mem_id)
    assert mem_after is None

    # Verify no longer in active or superseded
    active = engine.store.get_user_memories("forget_test", include_superseded=False)
    superseded = engine.store.get_user_memories("forget_test", include_superseded=True)

    assert not any(mem.id == mem_id for mem in active)
    assert not any(mem.id == mem_id for mem in superseded)