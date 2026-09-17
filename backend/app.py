import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.memory.engine import ChronosMemoryEngine
from backend.memory.models import ChatRequest, ChatResponse, MemoryEntry, MemoryStatus
from backend.seed_data import seed_database

app = FastAPI(
    title="MemoryOS API",
    description="The Assistant That Never Forgets... Or Does It? Persistent & Contradiction-Aware Memory Engine",
    version="1.0.0"
)

# Enable CORS for frontend Vite dev server & production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = ChronosMemoryEngine()

# Initialize with sample data if fresh database
try:
    existing_riku = engine.store.get_user_memories("riku")
    if not existing_riku:
        seed_database(engine)
except Exception as e:
    print("Startup seed note:", e)

class ForgetRequest(BaseModel):
    user_id: str
    target: str # either a memory_id or a keyword/target phrase
    reason: Optional[str] = "User requested deletion"

class ResetRequest(BaseModel):
    user_id: Optional[str] = None # None means reset all

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    try:
        response = engine.process_chat(req)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memories")
def get_memories(
    user_id: str = "riku",
    include_superseded: bool = True,
    include_forgotten: bool = False,
    query: Optional[str] = None
):
    try:
        if query and query.strip():
            res = engine.retrieve_with_attribution(user_id=user_id, query=query, top_k=10)
            return {
                "user_id": user_id,
                "memories": [m.dict() for m in res.all_retrieved],
                "attributions": [a.dict() for a in res.attributions]
            }
        memories = engine.store.get_user_memories(
            user_id=user_id,
            include_superseded=include_superseded,
            include_forgotten=include_forgotten
        )
        return {
            "user_id": user_id,
            "memories": [m.dict() for m in memories],
            "total_count": len(memories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge-graph")
def get_knowledge_graph(user_id: str = "riku"):
    try:
        graph = engine.get_knowledge_graph(user_id)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/timeline")
def get_timeline(user_id: str = "riku"):
    try:
        events = engine.get_timeline_events(user_id)
        return {"user_id": user_id, "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
def get_history(user_id: str = "riku", session_id: Optional[str] = None):
    try:
        history = engine.store.get_chat_history(user_id=user_id, session_id=session_id)
        return {"user_id": user_id, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/forget")
def forget_endpoint(req: ForgetRequest):
    try:
        # Check if target is a UUID memory_id
        mem = engine.store.get_memory(req.target)
        if mem and mem.user_id == req.user_id:
            success = engine.store.forget_memory(mem.id, user_id=req.user_id, reason=req.reason)
            return {"success": success, "message": f"Memory ID #{req.target[:8]} successfully purged."}
        
        # Otherwise treat as target search query
        candidates = engine.store.vector_search(req.user_id, req.target, top_k=5, min_similarity=0.2)
        purged = []
        for c_mem, score in candidates:
            if c_mem.status != MemoryStatus.FORGOTTEN:
                engine.store.forget_memory(c_mem.id, user_id=req.user_id, reason=req.reason)
                purged.append(c_mem.id)

        return {"success": True, "purged_count": len(purged), "purged_ids": purged}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
def reset_endpoint(req: ResetRequest):
    try:
        if req.user_id:
            engine.store.purge_user(req.user_id)
        else:
            seed_database(engine)
        return {"success": True, "message": "Database reset & re-seeded with demo benchmark scenarios."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
def list_users():
    users = ["riku", "vansh", "sid"]
    user_stats = []
    for u in users:
        mems = engine.store.get_user_memories(u, include_superseded=True)
        active_count = len([m for m in mems if m.status == MemoryStatus.ACTIVE])
        superseded_count = len([m for m in mems if m.status == MemoryStatus.SUPERSEDED])
        user_stats.append({
            "user_id": u,
            "total_memories": len(mems),
            "active_memories": active_count,
            "superseded_memories": superseded_count
        })
    return {"users": user_stats}

# Serve frontend build if exists
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
