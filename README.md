# MemoryOS: The Persistent & Contradiction-Aware AI Assistant

> **"A search engine finds facts. MemoryOS tracks the evolution of truth over time."**

MemoryOS is an AI assistant built for the track **"The Assistant That Never Forgets... Or Does It?"**. Rather than naively dumping raw text into a vector store and retrieving top-$k$ stale chunks, MemoryOS implements a complete **Cognitive Belief Architecture** that tracks people, evolving preferences, architecture decisions, and temporal validity over time across sessions, users, and conversations.

---

## 🌟 Key Features & Track Requirements Fulfillment

### 1. Cross-Session True Persistence
- Backed by persistent SQLite and dense semantic vector indexing.
- Closing, restarting, or reopening the app preserves full state, historical evolution, and audit trails.

### 2. Contradiction Resolution & Temporal Mutation
- Detects opposing/mutually exclusive assertions across sessions (e.g. *Day 1: "I live in Seattle"* ➔ *Day 3: "I moved to Tokyo"*).
- Automatically marks the older memory as `SUPERSEDED`, links it to the new memory (`superseded_by_id`), records validity intervals (`[valid_from, valid_to]`), and writes an explanation reason into the historical record.

### 3. Clear Memory Lifecycle Policy (What to Keep, Update, Decay, Forget)
- **Profile Facts & Decisions**: High importance, long half-life, updated on contradiction.
- **Preferences**: Tracked and replaced upon explicit reversals (*"I quit coffee, only drink matcha"*).
- **Time-Bound Events**: Automatically transition to `EXPIRED` once their scheduled date passes.
- **Ephemeral Chit-Chat**: Filtered or decayed rapidly via half-life recency decay.
- **GDPR Selective Forgetting**: Targeted cryptographic erasure (*"Forget my phone number"*).

### 4. 100% Explainable Attribution Trace
- Every assistant response transparently displays:
  - Exact **Active Memories** used (with IDs, text, similarity scores, intervals).
  - **Superseded Memories** that were filtered out with specific reasons.
  - **Conflict Resolution notes** describing how contradictions were reconciled.

### 5. Strict Multi-Tenant Privacy Isolation
- Complete memory separation by `user_id` (Riku, Vansh, Sid). Riku's confidential projects are mathematically invisible to Vansh.

### 6. Interactive Visualizer & Live Judge Benchmarks
- **Belief Knowledge Graph**: Real-time canvas visualization of active beliefs (emerald), superseded states (amber), and mutation lineage vectors (red dashed).
- **Temporal Lineage**: Chronological scrubber tracing state changes over time.
- **1-Click Live Judge Benchmarks**: Automated live interactive tests for live judging.

---

## 🚀 Quick Start

### 1. Automated 1-Click Launch
Double-click `run.bat` or run:
```powershell
.\run.bat
```

### 2. Running Automated Tests
```powershell
pytest backend/tests/test_memory.py -v
```

### 3. Manual Server Launch
```powershell
# Backend (FastAPI)
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload

# Frontend (Vite + React)
cd frontend
npm run dev
```

Open your browser to: **http://localhost:5173** (or http://127.0.0.1:8000).

---

## 🧪 Live Judge Benchmark Scenarios

In the web application, click the **"Judge Benchmarks"** tab:
1. **Benchmark 1 (Relocation Conflict)**: Validates Day 1 Seattle ➔ Day 3 Tokyo state mutation & attribution.
2. **Benchmark 2 (Diet Preference Reversal)**: Validates Keto ➔ Vegan diet transition and preference invalidation.
3. **Benchmark 3 (Multi-User Privacy Barrier)**: Validates zero cross-tenant contamination between Riku and Vansh.
4. **Benchmark 4 (Targeted GDPR Purge)**: Validates selective memory erasure and audit log generation.
