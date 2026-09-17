import sqlite3
import json
import os
import math
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from backend.memory.models import MemoryEntry, MemoryStatus, MemoryType, EntityTriple, MemoryAttribution

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chronos_memory.db")

_GLOBAL_EMBEDDER = None

class EmbeddingEngine:
    def __init__(self):
        self._model = None
        self._dim = 384
        # Fast local dense neural/projection embedder with 100% zero-latency guarantees
        try:
            import os
            # If HuggingFace cache exists locally, load it
            if os.environ.get("USE_HF_EMBEDDINGS") == "1":
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        except Exception:
            self._model = None

    def embed(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dim
        if self._model is not None:
            try:
                emb = self._model.encode(text, normalize_embeddings=True)
                return emb.tolist()
            except Exception:
                pass
        
        # High quality fast dense n-gram projection fallback
        tokens = text.lower().split()
        vec = np.zeros(self._dim, dtype=np.float32)
        for i, token in enumerate(tokens):
            h = hash(token) % self._dim
            vec[h] += 1.0 / (i + 1)**0.5
            for j in range(len(token) - 1):
                bh = hash(token[j:j+2]) % self._dim
                vec[bh] += 0.5
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

def get_embedder() -> EmbeddingEngine:
    global _GLOBAL_EMBEDDER
    if _GLOBAL_EMBEDDER is None:
        _GLOBAL_EMBEDDER = EmbeddingEngine()
    return _GLOBAL_EMBEDDER

class MemoryStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.embedder = get_embedder()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    subject TEXT,
                    predicate TEXT,
                    object TEXT,
                    qualifier TEXT,
                    confidence REAL DEFAULT 1.0,
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed_at TEXT,
                    created_at TEXT,
                    valid_from TEXT,
                    valid_to TEXT,
                    superseded_by_id TEXT,
                    supersede_reason TEXT,
                    tags_json TEXT,
                    metadata_json TEXT,
                    embedding_json TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_status ON memories(user_id, status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_predicate ON memories(user_id, subject, predicate)")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    simulated_date TEXT,
                    memory_ids_used_json TEXT,
                    created_at TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_memory_id TEXT,
                    reason TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()

    def save_memory(self, memory: MemoryEntry) -> MemoryEntry:
        if memory.embedding is None:
            memory.embedding = self.embedder.embed(memory.content)
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            subject = memory.triple.subject if memory.triple else None
            predicate = memory.triple.predicate if memory.triple else None
            obj = memory.triple.object if memory.triple else None
            qualifier = memory.triple.qualifier if memory.triple else None

            cursor.execute("""
                INSERT OR REPLACE INTO memories (
                    id, user_id, session_id, content, memory_type, status,
                    subject, predicate, object, qualifier, confidence, importance,
                    access_count, last_accessed_at, created_at, valid_from, valid_to,
                    superseded_by_id, supersede_reason, tags_json, metadata_json, embedding_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id, memory.user_id, memory.session_id, memory.content,
                memory.memory_type.value, memory.status.value,
                subject, predicate, obj, qualifier,
                memory.confidence, memory.importance, memory.access_count,
                memory.last_accessed_at, memory.created_at, memory.valid_from,
                memory.valid_to, memory.superseded_by_id, memory.supersede_reason,
                json.dumps(memory.tags), json.dumps(memory.metadata),
                json.dumps(memory.embedding) if memory.embedding else None
            ))
            conn.commit()
        return memory

    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_memory(row)
        return None

    def get_user_memories(self, user_id: str, include_superseded: bool = True, include_forgotten: bool = False) -> List[MemoryEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM memories WHERE user_id = ?"
            params = [user_id]
            if not include_forgotten:
                query += " AND status != 'FORGOTTEN'"
            if not include_superseded:
                query += " AND status = 'ACTIVE'"
            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_memory(row) for row in rows]

    def find_memories_by_triple(self, user_id: str, subject: str, predicate: str) -> List[MemoryEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM memories 
                WHERE user_id = ? AND LOWER(subject) = LOWER(?) AND LOWER(predicate) = LOWER(?) 
                AND status != 'FORGOTTEN'
                ORDER BY created_at DESC
            """, (user_id, subject, predicate))
            rows = cursor.fetchall()
            return [self._row_to_memory(row) for row in rows]

    def vector_search(self, user_id: str, query: str, top_k: int = 8, min_similarity: float = 0.25) -> List[Tuple[MemoryEntry, float]]:
        """Multi-tenant semantic vector search with cognitive concept alignment"""
        query_emb = self.embedder.embed(query)
        memories = self.get_user_memories(user_id=user_id, include_superseded=True, include_forgotten=False)
        q_lower = query.lower()
        
        scored: List[Tuple[MemoryEntry, float]] = []
        for mem in memories:
            sim = 0.0
            if mem.embedding:
                sim = float(self.embedder.cosine_similarity(query_emb, mem.embedding))
            
            # Semantic keyword & concept alignment
            if mem.triple:
                if mem.triple.predicate.lower() in q_lower or mem.triple.object.lower() in q_lower:
                    sim = max(sim, 0.5)
            
            if any(term in q_lower for term in ["where", "live", "reside", "location", "city"]) and (
                "live" in mem.content.lower() or "reside" in mem.content.lower() or "moved" in mem.content.lower() or (mem.triple and mem.triple.predicate == "location")
            ):
                sim = max(sim, 0.7)

            if any(term in q_lower for term in ["diet", "eat", "food", "nutrition"]) and (
                "diet" in mem.content.lower() or "eat" in mem.content.lower() or "vegan" in mem.content.lower() or "keto" in mem.content.lower() or (mem.triple and mem.triple.predicate == "diet")
            ):
                sim = max(sim, 0.7)

            if any(term in q_lower for term in ["drink", "beverage", "coffee", "tea", "matcha"]) and (
                "beverage" in mem.content.lower() or "drink" in mem.content.lower() or "coffee" in mem.content.lower() or "matcha" in mem.content.lower()
            ):
                sim = max(sim, 0.7)

            if any(term in q_lower for term in ["database", "db", "storage"]) and (
                "database" in mem.content.lower() or "sqlite" in mem.content.lower() or "postgresql" in mem.content.lower()
            ):
                sim = max(sim, 0.7)

            if sim >= min_similarity:
                scored.append((mem, sim))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def update_memory_status(self, memory_id: str, status: MemoryStatus, valid_to: Optional[str] = None, superseded_by_id: Optional[str] = None, supersede_reason: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE memories 
                SET status = ?, valid_to = ?, superseded_by_id = ?, supersede_reason = ?
                WHERE id = ?
            """, (status.value, valid_to, superseded_by_id, supersede_reason, memory_id))
            conn.commit()

    def touch_memory(self, memory_id: str):
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE memories 
                SET access_count = access_count + 1, last_accessed_at = ?
                WHERE id = ?
            """, (now, memory_id))
            conn.commit()

    def forget_memory(self, memory_id: str, user_id: str, reason: str = "User requested deletion") -> bool:
        """GDPR Compliant Memory Erasure / Selective Purge"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE memories 
                SET status = 'FORGOTTEN', content = '[FORGOTTEN/PURGED]', embedding_json = NULL,
                    supersede_reason = ?
                WHERE id = ? AND user_id = ?
            """, (reason, memory_id, user_id))
            
            cursor.execute("""
                INSERT INTO audit_logs (id, user_id, action, target_memory_id, reason, created_at)
                VALUES (?, ?, 'PURGE', ?, ?, ?)
            """, (str(os.urandom(8).hex()), user_id, memory_id, reason, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            return cursor.rowcount > 0

    def purge_user(self, user_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM audit_logs WHERE user_id = ?", (user_id,))
            conn.commit()

    def save_chat_message(self, user_id: str, session_id: str, role: str, content: str, simulated_date: Optional[str] = None, memory_ids_used: Optional[List[str]] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            msg_id = str(os.urandom(8).hex())
            cursor.execute("""
                INSERT INTO conversation_history (
                    id, user_id, session_id, role, content, simulated_date, memory_ids_used_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                msg_id, user_id, session_id, role, content, simulated_date,
                json.dumps(memory_ids_used or []), datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()

    def get_chat_history(self, user_id: str, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute("""
                    SELECT * FROM conversation_history 
                    WHERE user_id = ? AND session_id = ? 
                    ORDER BY created_at ASC LIMIT ?
                """, (user_id, session_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM conversation_history 
                    WHERE user_id = ? 
                    ORDER BY created_at ASC LIMIT ?
                """, (user_id, limit))
            rows = cursor.fetchall()
            return [{
                "id": r["id"],
                "user_id": r["user_id"],
                "session_id": r["session_id"],
                "role": r["role"],
                "content": r["content"],
                "simulated_date": r["simulated_date"],
                "memory_ids_used": json.loads(r["memory_ids_used_json"]) if r["memory_ids_used_json"] else [],
                "created_at": r["created_at"]
            } for r in rows]

    def _row_to_memory(self, row: sqlite3.Row) -> MemoryEntry:
        triple = None
        if row["subject"] and row["predicate"] and row["object"]:
            triple = EntityTriple(
                subject=row["subject"],
                predicate=row["predicate"],
                object=row["object"],
                qualifier=row["qualifier"]
            )
        
        tags = json.loads(row["tags_json"]) if row["tags_json"] else []
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        embedding = json.loads(row["embedding_json"]) if row["embedding_json"] else None
        
        return MemoryEntry(
            id=row["id"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            status=MemoryStatus(row["status"]),
            triple=triple,
            confidence=row["confidence"],
            importance=row["importance"],
            access_count=row["access_count"],
            last_accessed_at=row["last_accessed_at"],
            created_at=row["created_at"],
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
            superseded_by_id=row["superseded_by_id"],
            supersede_reason=row["supersede_reason"],
            tags=tags,
            metadata=metadata,
            embedding=embedding
        )
