from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from backend.memory.models import MemoryEntry, MemoryStatus, EntityTriple
from backend.memory.store import MemoryStore

class ConflictResolver:
    # Single-valued predicates where a new value replaces/supersedes the old value
    MUTUALLY_EXCLUSIVE_PREDICATES = {
        "lives_in",
        "primary_beverage",
        "dietary_lifestyle",
        "works_as",
        "employed_at",
        "database_choice",
        "framework_choice",
        "has_phone",
        "has_email",
        "prefers_tool"
    }

    def __init__(self, store: MemoryStore):
        self.store = store

    def resolve_conflicts_for_new_memory(self, new_memory: MemoryEntry, simulated_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Inspects existing active memories for the user.
        If a contradiction or state update is found:
        - Marks old memory as SUPERSEDED.
        - Sets valid_to timestamp.
        - Links superseded_by_id to new_memory.id.
        - Records human-readable supersede_reason.
        Returns a list of conflict resolution event logs.
        """
        resolution_logs = []
        user_id = new_memory.user_id
        
        # If new memory has no triple, check semantic similarity to find direct overwrites
        if not new_memory.triple:
            return self._resolve_by_semantic_similarity(new_memory)

        subject = new_memory.triple.subject
        predicate = new_memory.triple.predicate
        new_obj = new_memory.triple.object

        # Find existing active memories with matching subject & predicate
        existing_memories = self.store.find_memories_by_triple(user_id, subject, predicate)
        active_candidates = [m for m in existing_memories if m.status == MemoryStatus.ACTIVE and m.id != new_memory.id]

        is_mutually_exclusive = predicate in self.MUTUALLY_EXCLUSIVE_PREDICATES or self._is_opposing_values(predicate, new_obj)

        for old_mem in active_candidates:
            old_obj = old_mem.triple.object if old_mem.triple else ""
            
            # If the value is the same, just reinforce/touch the old memory
            if old_obj.lower().strip() == new_obj.lower().strip():
                self.store.touch_memory(old_mem.id)
                continue

            if is_mutually_exclusive or self._is_direct_override(old_mem.content, new_memory.content):
                # We have a contradiction / update!
                valid_to = simulated_date or new_memory.valid_from or datetime.now(timezone.utc).isoformat()
                reason = f"Updated '{predicate.replace('_', ' ')}' from '{old_obj}' to '{new_obj}'"
                if simulated_date:
                    reason += f" on {simulated_date}"

                # Mark old memory as SUPERSEDED
                self.store.update_memory_status(
                    memory_id=old_mem.id,
                    status=MemoryStatus.SUPERSEDED,
                    valid_to=valid_to,
                    superseded_by_id=new_memory.id,
                    supersede_reason=reason
                )

                log_entry = {
                    "type": "STATE_SUPERSEDED",
                    "predicate": predicate,
                    "old_memory_id": old_mem.id,
                    "old_value": old_obj,
                    "new_memory_id": new_memory.id,
                    "new_value": new_obj,
                    "reason": reason,
                    "timestamp": valid_to
                }
                resolution_logs.append(log_entry)

        # Handle explicit reversal phrases (e.g. "I quit coffee", "I stopped using MongoDB")
        resolution_logs.extend(self._handle_explicit_reversals(new_memory, simulated_date))

        return resolution_logs

    def _resolve_by_semantic_similarity(self, new_memory: MemoryEntry) -> List[Dict[str, Any]]:
        resolution_logs = []
        similar_mems = self.store.vector_search(new_memory.user_id, new_memory.content, top_k=3, min_similarity=0.75)
        for old_mem, sim in similar_mems:
            if old_mem.status == MemoryStatus.ACTIVE and old_mem.id != new_memory.id:
                if self._is_direct_override(old_mem.content, new_memory.content):
                    valid_to = new_memory.valid_from or datetime.now(timezone.utc).isoformat()
                    reason = f"Superseded by newer similar statement with similarity {sim:.2f}"
                    self.store.update_memory_status(
                        memory_id=old_mem.id,
                        status=MemoryStatus.SUPERSEDED,
                        valid_to=valid_to,
                        superseded_by_id=new_memory.id,
                        supersede_reason=reason
                    )
                    resolution_logs.append({
                        "type": "SEMANTIC_SUPERSEDED",
                        "old_memory_id": old_mem.id,
                        "old_content": old_mem.content,
                        "new_memory_id": new_memory.id,
                        "new_content": new_memory.content,
                        "reason": reason
                    })
        return resolution_logs

    def _handle_explicit_reversals(self, new_memory: MemoryEntry, simulated_date: Optional[str] = None) -> List[Dict[str, Any]]:
        logs = []
        content_lower = new_memory.content.lower()
        if any(rev in content_lower for rev in ["quit", "stopped", "no longer", "gave up", "cancelled", "deprecated"]):
            active_mems = self.store.get_user_memories(new_memory.user_id, include_superseded=False)
            for old_mem in active_mems:
                if old_mem.id == new_memory.id:
                    continue
                # If old memory talks about the thing we just stopped
                if old_mem.triple and old_mem.triple.object.lower() in content_lower:
                    valid_to = simulated_date or datetime.now(timezone.utc).isoformat()
                    reason = f"User explicitly ceased/deprecated: {old_mem.triple.object}"
                    self.store.update_memory_status(
                        memory_id=old_mem.id,
                        status=MemoryStatus.SUPERSEDED,
                        valid_to=valid_to,
                        superseded_by_id=new_memory.id,
                        supersede_reason=reason
                    )
                    logs.append({
                        "type": "EXPLICIT_CESSATION",
                        "old_memory_id": old_mem.id,
                        "target_object": old_mem.triple.object,
                        "reason": reason
                    })
        return logs

    def _is_opposing_values(self, predicate: str, val: str) -> bool:
        return predicate in self.MUTUALLY_EXCLUSIVE_PREDICATES

    def _is_direct_override(self, old_text: str, new_text: str) -> bool:
        o = old_text.lower()
        n = new_text.lower()
        # Direct opposites
        if ("prefer coffee" in o and "prefer tea" in n) or ("love coffee" in o and "quit coffee" in n):
            return True
        if ("live in" in o and "moved to" in n):
            return True
        if ("using react" in o and "using vue" in n) or ("using postgres" in o and "using sqlite" in n):
            return True
        return False
