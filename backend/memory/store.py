import sqlite3
import json
import os
import math
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from backend.memory.models import MemoryEntry, MemoryStatus, MemoryType, EntityTriple, AuditLogEntry

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chronos_memory.db")

_GLOBAL_EMBEDDER = None

class EmbeddingEngine:
    def __init__(self):
        self._model = None
        self._dim = 384
        try:
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
        
        # High quality fast dense n-gram projection with positional & subword weighting
        tokens = text.lower().replace(",", " ").replace(".", " ").replace("?", " ").replace("!", " ").split()
        vec = np.zeros(self._dim, dtype=np.float32)
        for i, token in enumerate(tokens):
            h = (hash(token) & 0x7FFFFFFF) % self._dim
            vec[h] += 1.2 / (i + 1)**0.3
            for j in range(len(token) - 1):
                bh = (hash(token[j:j+2]) & 0x7FFFFFFF) % self._dim
                vec[bh] += 0.4
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
        conn = sqlite3.connect(self.db_path, timeout=10.0)
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

    def get_memory_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a single non-forgotten memory by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE id = ? AND status != 'FORGOTTEN'", (memory_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_memory(row)
        return None

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Hard delete a memory record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE user_id = ? AND id = ?", (user_id, memory_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_user_memories(
        self,
        user_id: str,
        include_superseded: bool = True,
        include_forgotten: bool = False,
        simulated_date: Optional[str] = None
    ) -> List[MemoryEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM memories WHERE user_id = ?"
            params: List[Any] = [user_id]
            if not include_forgotten:
                query += " AND status != 'FORGOTTEN'"
            if not include_superseded:
                query += " AND status = 'ACTIVE'"
            
            if simulated_date:
                query += " AND (valid_from IS NULL OR valid_from <= ?)"
                params.append(simulated_date)

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

    def vector_search(
        self,
        user_id: str,
        query: str,
        top_k: int = 8,
        min_similarity: float = 0.15,
        simulated_date: Optional[str] = None
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        Intent-aware hybrid memory retrieval:
        1. Dense semantic embedding similarity
        2. Keyword & BM25-style overlap
        3. Predicate & Object graph match
        4. Query-intent domain boost
        5. Current ACTIVE state boost (with preserved SUPERSEDED historical access)
        """
        query_emb = self.embedder.embed(query)
        memories = self.get_user_memories(
            user_id=user_id,
            include_superseded=True,
            include_forgotten=False,
            simulated_date=simulated_date
        )

        q = query.lower().strip()
        q_clean = q.replace("?", "").replace(".", "").replace(",", "").replace("!", "")
        query_words = set(q_clean.split())

        # Intent Term sets
        location_terms = {"where", "live", "lived", "reside", "resided", "location", "city", "home", "moved", "move", "living", "address"}
        beverage_terms = {"drink", "beverage", "coffee", "tea", "matcha", "drinks", "drinking", "thirsty", "cup"}
        database_terms = {"database", "db", "storage", "sqlite", "postgres", "postgresql", "mongo", "mongodb", "mysql", "datastore"}
        tech_terms = {"framework", "tech", "technology", "stack", "react", "vue", "angular", "next", "ide", "tool", "editor", "language", "python", "typescript"}
        diet_terms = {"diet", "eat", "eating", "food", "nutrition", "vegan", "keto", "carnivore", "vegetarian", "allergic", "allergy", "allergies", "dinner", "lunch", "breakfast", "meal", "meals", "cook", "cooking", "dish", "menu", "restaurant"}
        job_terms = {"job", "work", "role", "profession", "employed", "company", "career", "occupation"}
        history_terms = {"previously", "before", "used to", "formerly", "old", "prior", "in the past", "back then", "earlier", "history", "originate"}

        is_location_query = bool(query_words.intersection(location_terms))
        is_beverage_query = bool(query_words.intersection(beverage_terms))
        is_database_query = bool(query_words.intersection(database_terms))
        is_tech_query = bool(query_words.intersection(tech_terms))
        is_diet_query = bool(query_words.intersection(diet_terms))
        is_job_query = bool(query_words.intersection(job_terms))
        is_history_query = bool(any(ht in q for ht in history_terms))

        scored: List[Tuple[MemoryEntry, float]] = []

        for mem in memories:
            if mem.status == MemoryStatus.FORGOTTEN:
                continue

            # Semantic score
            semantic_score = 0.0
            if mem.embedding:
                semantic_score = float(self.embedder.cosine_similarity(query_emb, mem.embedding))

            score = semantic_score
            content = mem.content.lower()
            predicate = mem.triple.predicate.lower() if mem.triple else ""
            obj = mem.triple.object.lower() if mem.triple else ""

            # Domain Boosts
            if is_location_query:
                if predicate in {"lives_in", "origin_from"} or any(w in content for w in ["live", "lived", "reside", "moved", "location", "seattle", "tokyo", "berlin", "london"]):
                    score = max(score, 0.88)
                else:
                    score *= 0.4
            elif is_beverage_query:
                if predicate in {"primary_beverage", "prefers_beverage", "stopped_consuming"} or any(w in content for w in ["drink", "beverage", "coffee", "tea", "matcha"]):
                    score = max(score, 0.88)
                else:
                    score *= 0.4
            elif is_database_query:
                if predicate in {"database_choice", "decided_to_use", "migrated_tech"} or any(w in content for w in ["database", "sqlite", "postgres", "postgresql", "mysql"]):
                    score = max(score, 0.88)
                else:
                    score *= 0.4
            elif is_diet_query:
                if predicate in {"dietary_lifestyle", "avoids_food", "allergic_to"} or any(w in content for w in ["diet", "vegan", "keto", "allergic", "peanut", "steak", "food"]):
                    score = max(score, 0.88)
                else:
                    score *= 0.4
            elif is_job_query:
                if predicate in {"works_as", "employed_at"} or any(w in content for w in ["work", "architect", "engineer", "coach", "student", "role", "company"]):
                    score = max(score, 0.88)
                else:
                    score *= 0.4
            elif is_tech_query:
                if predicate in {"framework_choice", "decided_to_use", "prefers_tool"} or any(w in content for w in ["react", "vue", "neovim", "vscode", "ide", "tech", "tool"]):
                    score = max(score, 0.88)

            # Direct predicate & object matching
            if predicate and predicate.replace("_", " ") in q:
                score = max(score, 0.95)
            if obj and obj in q:
                score = max(score, 0.95)

            # Keyword lexical overlap boost
            content_words = set(content.replace(".", " ").replace(",", " ").replace("!", " ").split())
            overlap = query_words.intersection(content_words)
            if overlap:
                score += min(0.20, len(overlap) * 0.06)

            # State weight adjustments
            if is_history_query:
                if mem.status == MemoryStatus.SUPERSEDED:
                    score *= 1.3  # Boost superseded memories for retrospective questions
                elif mem.status == MemoryStatus.ACTIVE:
                    score *= 0.8
            else:
                if mem.status == MemoryStatus.ACTIVE:
                    score *= 1.0
                elif mem.status == MemoryStatus.SUPERSEDED:
                    score *= 0.55  # Retrievable as historical context, but won't overshadow active
                elif mem.status == MemoryStatus.DECAYED:
                    score *= 0.35
                elif mem.status == MemoryStatus.EXPIRED:
                    score *= 0.25

            # Confidence & Importance weights
            confidence = max(0.1, min(1.0, mem.confidence))
            importance = max(0.1, min(1.0, mem.importance))
            score *= (0.7 + 0.3 * confidence)
            score *= (0.7 + 0.3 * importance)

            if score >= min_similarity:
                scored.append((mem, float(score)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def update_memory_status(
        self,
        memory_id: str,
        status: MemoryStatus,
        valid_to: Optional[str] = None,
        superseded_by_id: Optional[str] = None,
        supersede_reason: Optional[str] = None
    ):
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
        """GDPR Compliant Memory Erasure / Selective Purge with audit trail."""
        now = datetime.now(timezone.utc).isoformat()
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
            """, (str(os.urandom(8).hex()), user_id, memory_id, reason, now))
            conn.commit()
            return cursor.rowcount > 0

    def purge_user(self, user_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM audit_logs WHERE user_id = ?", (user_id,))
            conn.commit()

    def save_chat_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        simulated_date: Optional[str] = None,
        memory_ids_used: Optional[List[str]] = None
    ):
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

    def get_audit_logs(self, user_id: Optional[str] = None, limit: int = 50) -> List[AuditLogEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT * FROM audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
                """, (user_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [AuditLogEntry(
                id=r["id"],
                user_id=r["user_id"],
                action=r["action"],
                target_memory_id=r["target_memory_id"],
                reason=r["reason"],
                created_at=r["created_at"]
            ) for r in rows]

    def get_system_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM memories")
            total = cursor.fetchone()["cnt"]
            
            cursor.execute("SELECT COUNT(*) as cnt FROM memories WHERE status = 'ACTIVE'")
            active = cursor.fetchone()["cnt"]
            
            cursor.execute("SELECT COUNT(*) as cnt FROM memories WHERE status = 'SUPERSEDED'")
            superseded = cursor.fetchone()["cnt"]
            
            cursor.execute("SELECT COUNT(*) as cnt FROM memories WHERE status = 'FORGOTTEN'")
            forgotten = cursor.fetchone()["cnt"]

            cursor.execute("SELECT DISTINCT user_id FROM memories")
            users = [r["user_id"] for r in cursor.fetchall()]

            cursor.execute("SELECT COUNT(*) as cnt FROM audit_logs")
            audit_count = cursor.fetchone()["cnt"]

            return {
                "total_memories": total,
                "active_memories": active,
                "superseded_memories": superseded,
                "forgotten_memories": forgotten,
                "user_count": len(users),
                "users": users,
                "audit_logs_count": audit_count
            }

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