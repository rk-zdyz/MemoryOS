import os
import pytest
import uuid
import tempfile
from backend.memory.engine import ChronosMemoryEngine
from backend.memory.models import ChatRequest, MemoryStatus, MemoryType

@pytest.fixture
def engine():
    # Use a temporary database path
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, f"test_chronos_{uuid.uuid4().hex[:8]}.db")
    eng = ChronosMemoryEngine(db_path=test_db)
    yield eng
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
    except Exception:
        pass

def test_cross_session_persistence(engine):
    db_file = engine.store.db_path
    # Session 1: State fact
    req1 = ChatRequest(user_id="user_test", session_id="s1", message="I live in San Francisco.")
    resp1 = engine.process_chat(req1)
    assert len(resp1.new_memories_extracted) > 0

    # Simulate full engine restart (reopening app with same DB)
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

def test_active_memory_beats_superseded_in_retrieval(engine):
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

    # Search for current location
    results = engine.store.vector_search(
        user_id="retrieval_test",
        query="Where do I live?",
        top_k=5,
        min_similarity=0.15
    )
    assert len(results) >= 2
    top_memory = results[0][0]
    assert top_memory.status == MemoryStatus.ACTIVE
    assert "Tokyo" in top_memory.content

def test_historical_query_retrieves_superseded(engine):
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

    resp = engine.process_chat(ChatRequest(
        user_id="history_test",
        message="Where did I live before Tokyo?"
    ))
    assert "Seattle" in resp.answer

def test_multi_user_privacy_isolation(engine):
    # Riku declares confidential project
    engine.process_chat(ChatRequest(user_id="riku", message="My confidential project is codenamed TitanOmega."))
    
    # Vansh asks about secret project
    vansh_resp = engine.process_chat(ChatRequest(user_id="vansh", message="What is my confidential project codename?"))
    assert "TitanOmega" not in vansh_resp.answer
    assert len(vansh_resp.used_memories) == 0

def test_selective_forgetting_gdpr(engine):
    # User provides phone number
    r = engine.process_chat(ChatRequest(user_id="riku", message="My phone number is +1-555-0199."))
    mems = engine.store.get_user_memories("riku", include_superseded=False)
    assert any("555-0199" in m.content for m in mems)

    # User issues targeted forget command
    forget_resp = engine.process_chat(ChatRequest(user_id="riku", message="Forget my phone number."))
    assert "purged" in forget_resp.answer.lower()

    # Verify memory is wiped
    mems_after = engine.store.get_user_memories("riku", include_superseded=False, include_forgotten=False)
    assert not any("555-0199" in m.content for m in mems_after)

    # Verify audit log was created
    audit_logs = engine.store.get_audit_logs(user_id="riku")
    assert len(audit_logs) >= 1
    assert audit_logs[0].action == "PURGE"

def test_diet_preference_evolution(engine):
    # Day 1: Keto
    engine.process_chat(ChatRequest(
        user_id="vansh",
        session_id="v1",
        message="I eat a heavy keto carnivore diet with steak.",
        simulated_date="2026-09-02T10:00:00Z"
    ))
    
    # Day 2: Vegan
    engine.process_chat(ChatRequest(
        user_id="vansh",
        session_id="v2",
        message="I switched to a strict vegan diet for health.",
        simulated_date="2026-09-04T10:00:00Z"
    ))

    resp = engine.process_chat(ChatRequest(
        user_id="vansh",
        message="What is my current diet?"
    ))
    assert "vegan" in resp.answer.lower()

def test_knowledge_graph_structure(engine):
    engine.process_chat(ChatRequest(user_id="riku", message="I live in Seattle."))
    engine.process_chat(ChatRequest(user_id="riku", message="I moved to Tokyo."))
    
    graph = engine.get_knowledge_graph("riku")
    assert "nodes" in graph and "edges" in graph
    assert len(graph["nodes"]) >= 3 # User + 2 memory nodes
    evolution_edges = [e for e in graph["edges"] if e.get("status") == "EVOLUTION"]
    assert len(evolution_edges) >= 1

def test_system_stats(engine):
    engine.process_chat(ChatRequest(user_id="riku", message="I live in Seattle."))
    stats = engine.store.get_system_stats()
    assert stats["total_memories"] >= 1
    assert "riku" in stats["users"]

def test_natural_language_variations(engine):
    # 1. Informal location: "i live in vegas"
    r1 = engine.process_chat(ChatRequest(user_id="alice", message="i live in vegas"))
    assert len(r1.new_memories_extracted) == 1
    assert r1.new_memories_extracted[0].triple.predicate == "lives_in"
    assert r1.new_memories_extracted[0].triple.object.lower() == "vegas"

    # Query location naturally
    q1 = engine.process_chat(ChatRequest(user_id="alice", message="where do i live?"))
    assert "vegas" in q1.answer.lower()

    # 2. Relocation with "stay in London"
    r2 = engine.process_chat(ChatRequest(user_id="alice", message="I stay in London now."))
    assert len(r2.conflict_resolution_notes) > 0
    assert r2.new_memories_extracted[0].triple.object.lower() == "london"

    q2 = engine.process_chat(ChatRequest(user_id="alice", message="where am i?"))
    assert "london" in q2.answer.lower()

    # 3. Beverage: "i drink matcha"
    r3 = engine.process_chat(ChatRequest(user_id="alice", message="i drink matcha"))
    assert r3.new_memories_extracted[0].triple.predicate == "primary_beverage"
    assert r3.new_memories_extracted[0].triple.object.lower() == "matcha"

    # 4. Tech choice: "we use postgres"
    r4 = engine.process_chat(ChatRequest(user_id="alice", message="we use postgres"))
    assert r4.new_memories_extracted[0].triple.predicate == "database_choice"
    assert r4.new_memories_extracted[0].triple.object.lower() == "postgres"

    # 5. Diet: "i am vegan"
    r5 = engine.process_chat(ChatRequest(user_id="alice", message="i am vegan"))
    assert r5.new_memories_extracted[0].triple.predicate == "dietary_lifestyle"
    assert "vegan" in r5.new_memories_extracted[0].triple.object.lower()