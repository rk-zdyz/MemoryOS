"""
End-to-end test runner for live judge benchmarks against running FastAPI server.
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"

def run_benchmarks():
    print("==================================================================")
    print("       RUNNING MEMORYOS LIVE JUDGE BENCHMARKS VIA REST API        ")
    print("==================================================================")
    
    # Check stats
    r = requests.get(f"{BASE_URL}/stats?user_id=riku")
    print(f"[*] /api/stats -> Status {r.status_code}: {r.json()}")
    assert r.status_code == 200, "Stats API failed"
    
    # ---------------------------------------------------------
    # Benchmark 1: Relocation Contradiction
    # ---------------------------------------------------------
    print("\n--- [BENCHMARK 1: Relocation Contradiction] ---")
    # Reset Riku
    requests.post(f"{BASE_URL}/reset", json={"user_id": "riku"})
    
    # Ingest Day 1
    r1 = requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "I live in Seattle, Washington.",
        "simulated_date": "2026-01-01"
    }).json()
    print(f"Day 1 Ingestion Answer: {r1['answer']}")
    
    # Ingest Day 3 (Relocation)
    r2 = requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "I moved to Tokyo, Japan. I live in Tokyo now.",
        "simulated_date": "2026-01-03"
    }).json()
    print(f"Day 3 Relocation Answer: {r2['answer']}")
    
    # Query Current City
    r3 = requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "Where do I live right now?",
        "simulated_date": "2026-01-05"
    }).json()
    print(f"Query Answer: {r3['answer']}")
    print(f"Used Memories: {[m['content'] for m in r3['used_memories']]}")
    print(f"Superseded Memories: {[m['content'] for m in r3['superseded_memories']]}")
    
    assert "tokyo" in r3["answer"].lower(), "Tokyo not in current city response"
    assert any("tokyo" in m["content"].lower() for m in r3["used_memories"]), "Tokyo not in active attribution"
    assert any("seattle" in m["content"].lower() for m in r3["superseded_memories"]), "Seattle not in superseded attribution"
    print(">>> [PASS] Benchmark 1: Relocation Contradiction passed successfully!")

    # ---------------------------------------------------------
    # Benchmark 2: Dietary Preference Reversal
    # ---------------------------------------------------------
    print("\n--- [BENCHMARK 2: Dietary Preference Reversal] ---")
    requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "I follow a strict Keto diet, so I only eat low carb.",
        "simulated_date": "2026-01-01"
    })
    requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "I gave up keto and am strictly vegan now. No animal products.",
        "simulated_date": "2026-01-30"
    })
    r_diet = requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "What should I have for dinner?",
        "simulated_date": "2026-02-01"
    }).json()
    print(f"Diet Query Answer: {r_diet['answer']}")
    assert "vegan" in r_diet["answer"].lower(), "Vegan not in dinner response"
    assert any("vegan" in m["content"].lower() for m in r_diet["used_memories"]), "Vegan not in active attribution"
    assert any("keto" in m["content"].lower() for m in r_diet["superseded_memories"]), "Keto not in superseded attribution"
    print(">>> [PASS] Benchmark 2: Dietary Preference Reversal passed successfully!")

    # ---------------------------------------------------------
    # Benchmark 3: Multi-User Privacy Barrier
    # ---------------------------------------------------------
    print("\n--- [BENCHMARK 3: Multi-User Privacy Barrier] ---")
    # Ingest secret for Riku
    requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "My confidential project codename is Project Chimera.",
        "simulated_date": "2026-01-10"
    })
    # Query secret from Vansh
    r_vansh = requests.post(f"{BASE_URL}/chat", json={
        "user_id": "vansh",
        "message": "What is Riku's secret project codename?",
        "simulated_date": "2026-01-11"
    }).json()
    print(f"Vansh's Query Answer: {r_vansh['answer']}")
    assert "chimera" not in r_vansh["answer"].lower() or "don't have" in r_vansh["answer"].lower() or "no information" in r_vansh["answer"].lower(), "Cross-tenant leakage detected!"
    assert len([m for m in r_vansh["used_memories"] if "chimera" in m["content"].lower()]) == 0, "Leakage in Vansh's active memories"
    print(">>> [PASS] Benchmark 3: Multi-User Privacy Barrier passed successfully!")

    # ---------------------------------------------------------
    # Benchmark 4: Targeted GDPR Purge
    # ---------------------------------------------------------
    print("\n--- [BENCHMARK 4: Targeted GDPR Purge] ---")
    # Ingest phone number
    requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "My emergency contact number is +1-555-0199.",
        "simulated_date": "2026-01-01"
    })
    # Trigger forget
    f_res = requests.post(f"{BASE_URL}/forget", json={
        "user_id": "riku",
        "query": "phone number",
        "reason": "GDPR Article 17 Right to Erasure"
    }).json()
    print(f"Forget Response: {f_res}")
    assert f_res["forgotten_count"] >= 1, "Failed to purge memory"
    
    # Query again
    r_phone = requests.post(f"{BASE_URL}/chat", json={
        "user_id": "riku",
        "message": "What is my emergency phone number?",
        "simulated_date": "2026-01-02"
    }).json()
    print(f"Post-Purge Query: {r_phone['answer']}")
    assert "555-0199" not in r_phone["answer"], "Phone number still returned post-purge!"
    
    # Check audit log
    logs = requests.get(f"{BASE_URL}/audit-logs?user_id=riku").json()
    print(f"Audit Logs Count: {len(logs['logs'])}")
    assert len(logs["logs"]) >= 1, "Audit log was not written"
    print(">>> [PASS] Benchmark 4: Targeted GDPR Purge passed successfully!")
    
    # ---------------------------------------------------------
    # Check Knowledge Graph & Timeline Endpoints
    # ---------------------------------------------------------
    print("\n--- [CHECKING GRAPH & TIMELINE ENDPOINTS] ---")
    graph = requests.get(f"{BASE_URL}/knowledge-graph?user_id=riku").json()
    print(f"Graph Nodes: {len(graph['nodes'])}, Edges: {len(graph['edges'])}")
    assert len(graph["nodes"]) > 0, "No graph nodes found"
    
    timeline = requests.get(f"{BASE_URL}/timeline?user_id=riku").json()
    print(f"Timeline Events: {len(timeline['events'])}")
    assert len(timeline["events"]) > 0, "No timeline events found"
    
    print("\n==================================================================")
    print("         ALL 4 LIVE JUDGE BENCHMARKS PASSED (100% SUCCESS)        ")
    print("==================================================================")

if __name__ == "__main__":
    run_benchmarks()

