from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

class MemoryType(str, Enum):
    PROFILE_FACT = "PROFILE_FACT"       # User info, location, identity, roles, company
    PREFERENCE = "PREFERENCE"           # Likes, dislikes, tools, beverages, habits
    DECISION = "DECISION"               # Strategic choices, architecture decisions, tech stack
    EVENT_EPISODE = "EVENT_EPISODE"     # Time-bound meetings, trips, milestones
    TRANSIENT = "TRANSIENT"             # Chit-chat, casual remarks, low-value greetings

class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"                   # Currently valid and true
    SUPERSEDED = "SUPERSEDED"           # Outdated due to contradiction/update
    DECAYED = "DECAYED"                 # Diminished relevance due to lack of access/time
    EXPIRED = "EXPIRED"                 # Time-bound event whose validity has elapsed
    FORGOTTEN = "FORGOTTEN"             # Explicitly deleted by user (GDPR/purge)

class EntityTriple(BaseModel):
    subject: str = "User"
    predicate: str                      # e.g., "lives_in", "primary_beverage", "database_choice"
    object: str                         # e.g., "Tokyo", "Matcha", "SQLite-Vec"
    qualifier: Optional[str] = None     # e.g., "since 2026", "strictly"

class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "riku"
    session_id: str = "default_session"
    content: str
    memory_type: MemoryType = MemoryType.PROFILE_FACT
    status: MemoryStatus = MemoryStatus.ACTIVE
    triple: Optional[EntityTriple] = None
    confidence: float = 1.0             # 0.0 to 1.0
    importance: float = 0.5             # 0.0 to 1.0 (decay resistance)
    access_count: int = 0
    last_accessed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_from: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_to: Optional[str] = None      # When superseded or expired
    superseded_by_id: Optional[str] = None
    supersede_reason: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None

class MemoryAttribution(BaseModel):
    memory_id: str
    content: str
    memory_type: MemoryType
    status: MemoryStatus
    similarity_score: float
    confidence: float
    is_active: bool
    filter_reason: Optional[str] = None
    valid_interval: str
    created_at: str
    triple_repr: Optional[str] = None

class MemorySearchResult(BaseModel):
    active_memories: List[MemoryEntry] = Field(default_factory=list)
    superseded_memories: List[MemoryEntry] = Field(default_factory=list)
    decayed_memories: List[MemoryEntry] = Field(default_factory=list)
    all_retrieved: List[MemoryEntry] = Field(default_factory=list)
    attributions: List[MemoryAttribution] = Field(default_factory=list)
    conflict_detected: bool = False
    conflict_summary: Optional[str] = None

class ChatRequest(BaseModel):
    user_id: str = "riku"
    session_id: str = "session_1"
    message: str
    simulated_date: Optional[str] = None  # For time-travel tests (e.g., "2026-09-01T10:00:00Z")
    api_key: Optional[str] = None
    provider: Optional[str] = "local"     # local, gemini, openai

class ChatResponse(BaseModel):
    answer: str
    user_id: str
    session_id: str
    used_memories: List[MemoryAttribution] = Field(default_factory=list)
    superseded_memories: List[MemoryAttribution] = Field(default_factory=list)
    conflict_resolution_notes: List[str] = Field(default_factory=list)
    new_memories_extracted: List[MemoryEntry] = Field(default_factory=list)
    simulated_date: Optional[str] = None
    latency_ms: Optional[float] = None

class AuditLogEntry(BaseModel):
    id: str
    user_id: str
    action: str
    target_memory_id: Optional[str] = None
    reason: Optional[str] = None
    created_at: str

class ManualMemoryRequest(BaseModel):
    user_id: str = "riku"
    session_id: str = "manual_entry"
    content: str
    memory_type: MemoryType = MemoryType.PROFILE_FACT
    predicate: Optional[str] = None
    object: Optional[str] = None
    importance: float = 0.8
    simulated_date: Optional[str] = None

class ForgetRequest(BaseModel):
    user_id: str
    target: Optional[str] = None
    query: Optional[str] = None
    reason: Optional[str] = "User requested deletion"

    def get_target(self) -> str:
        return self.target or self.query or "all"

class ResetRequest(BaseModel):
    user_id: Optional[str] = None # None means reset all

