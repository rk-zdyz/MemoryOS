from backend.memory.engine import ChronosMemoryEngine
from backend.memory.models import ChatRequest

def seed_database(engine: ChronosMemoryEngine):
    print("[MemoryOS] Seeding realistic multi-user temporal scenarios...")
    
    # Reset existing test users to clean slate
    for u in ["riku", "vansh", "sid", "alice", "bob", "charlie"]:
        engine.store.purge_user(u)

    # ============================================================
    # Tenant 1: Riku (Software Architect - State Evolution & Contradictions)
    # Day 1: Seattle, Coffee, PostgreSQL
    # Day 3: Tokyo, Matcha, SQLite-Vec
    # ============================================================
    riku_day1 = [
        ("I live in Seattle.", "2026-09-01T09:00:00Z"),
        ("I work as a Lead Architect at CloudScale.", "2026-09-01T09:05:00Z"),
        ("My favorite beverage is dark roast coffee.", "2026-09-01T09:10:00Z"),
        ("We decided to use PostgreSQL as our primary database.", "2026-09-01T09:15:00Z")
    ]
    for msg, dt in riku_day1:
        engine.process_chat(ChatRequest(
            user_id="riku",
            session_id="session_day1",
            message=msg,
            simulated_date=dt
        ))

    riku_day3 = [
        ("I moved to Tokyo last weekend and currently reside there.", "2026-09-03T10:00:00Z"),
        ("I quit coffee completely; now I only drink matcha green tea.", "2026-09-03T10:15:00Z"),
        ("We migrated from PostgreSQL to SQLite-Vec for local-first speed.", "2026-09-03T10:30:00Z")
    ]
    for msg, dt in riku_day3:
        engine.process_chat(ChatRequest(
            user_id="riku",
            session_id="session_day3",
            message=msg,
            simulated_date=dt
        ))

    # ============================================================
    # Tenant 2: Vansh (Health Coach - Diet Pivot & GDPR Target)
    # Day 1: Berlin, Keto diet, Phone Number
    # Day 2: Vegan diet, Peanut allergy
    # ============================================================
    vansh_day1 = [
        ("I live in Berlin and work as a Fitness Coach.", "2026-09-02T08:00:00Z"),
        ("I eat a heavy keto carnivore diet with steak.", "2026-09-02T08:10:00Z"),
        ("My phone number is +49-151-8976543.", "2026-09-02T08:20:00Z")
    ]
    for msg, dt in vansh_day1:
        engine.process_chat(ChatRequest(
            user_id="vansh",
            session_id="vansh_session_1",
            message=msg,
            simulated_date=dt
        ))

    vansh_day2 = [
        ("I switched to a strict vegan diet for health.", "2026-09-04T12:00:00Z"),
        ("I am severely allergic to peanuts.", "2026-09-04T12:05:00Z")
    ]
    for msg, dt in vansh_day2:
        engine.process_chat(ChatRequest(
            user_id="vansh",
            session_id="vansh_session_2",
            message=msg,
            simulated_date=dt
        ))

    # ============================================================
    # Tenant 3: Sid (Student - Independent Tenant Isolation)
    # Day 1: London, Student UCL, Neovim IDE
    # ============================================================
    sid_day1 = [
        ("I live in London and study Computer Science at UCL.", "2026-09-05T14:00:00Z"),
        ("My favorite IDE is Neovim.", "2026-09-05T14:10:00Z")
    ]
    for msg, dt in sid_day1:
        engine.process_chat(ChatRequest(
            user_id="sid",
            session_id="sid_session_1",
            message=msg,
            simulated_date=dt
        ))

    print("[MemoryOS] Seeding complete! Loaded Riku, Vansh, and Sid.")

if __name__ == "__main__":
    eng = ChronosMemoryEngine()
    seed_database(eng)
