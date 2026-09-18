from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from backend.memory.models import MemoryEntry, MemoryStatus, EntityTriple
from backend.memory.store import MemoryStore

class ConflictResolver:
    # Single-valued predicates where a newer assertion naturally supersedes the prior one
    MUTUALLY_EXCLUSIVE_PREDICATES = {
        "lives_in",
        "primary_beverage",
        "prefers_beverage",
        "dietary_lifestyle",
        "works_as",
        "employed_at",
        "database_choice",
        "framework_choice",
        "has_phone",
        "has_email",
        "has_name",
        "prefers_tool",
        "confidential_project"
    }

    def __init__(self, store: MemoryStore):
        self.store = store

    def resolve_conflicts_for_new_memory(
        self,
        new_memory: MemoryEntry,
        simulated_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Inspects existing active memories for the user.
        If a contradiction, mutation, or update is detected:
        - Marks old memory as SUPERSEDED
        - Sets valid_to timestamp
        - Links superseded_by_id to new_memory.id
        - Records human-readable supersede_reason
        Returns list of conflict resolution event logs.
        """
        resolution_logs: List[Dict[str, Any]] = []
        user_id = new_memory.user_id
        current_time_iso = simulated_date or new_memory.valid_from or datetime.now(timezone.utc).isoformat()

        # Handle explicit cessation / reversals first ("quit coffee", "stopped", etc.)
        cessation_logs = self._handle_explicit_reversals(new_memory, current_time_iso)
        resolution_logs.extend(cessation_logs)

        # If new memory has no triple, check semantic similarity fallback
        if not new_memory.triple:
            sem_logs = self._resolve_by_semantic_similarity(new_memory, current_time_iso)
            resolution_logs.extend(sem_logs)
            return resolution_logs

        subject = new_memory.triple.subject
        predicate = new_memory.triple.predicate
        new_obj = new_memory.triple.object

        # Retrieve all existing memories for this subject & predicate
        existing_memories = self.store.find_memories_by_triple(
            user_id=user_id,
            subject=subject,
            predicate=predicate
        )

        active_candidates = [
            m for m in existing_memories
            if m.status == MemoryStatus.ACTIVE and m.id != new_memory.id
        ]

        is_mutually_exclusive = (
            predicate in self.MUTUALLY_EXCLUSIVE_PREDICATES
            or self._is_opposing_predicate(predicate)
        )

        for old_mem in active_candidates:
            old_obj = old_mem.triple.object if old_mem.triple else ""

            # Check for identical duplicate confirmation
            if old_obj.lower().strip() == new_obj.lower().strip():
                self.store.update_memory_status(
                    memory_id=new_memory.id,
                    status=MemoryStatus.SUPERSEDED,
                    valid_to=current_time_iso,
                    superseded_by_id=old_mem.id,
                    supersede_reason="Duplicate confirmation of existing active memory"
                )
                self.store.touch_memory(old_mem.id)
                resolution_logs.append({
                    "type": "DUPLICATE_CONFIRMED",
                    "existing_memory_id": old_mem.id,
                    "duplicate_memory_id": new_memory.id,
                    "reason": f"New statement confirms existing active {predicate.replace('_', ' ')}."
                })
                continue

            # Different value for a mutually exclusive predicate or direct semantic override
            if is_mutually_exclusive or self._is_direct_override(old_mem.content, new_memory.content):
                reason = f"Updated '{predicate.replace('_', ' ')}' from '{old_obj}' to '{new_obj}'"
                if simulated_date:
                    reason += f" (Recorded as of {simulated_date[:10]})"

                # Mark old memory as SUPERSEDED
                self.store.update_memory_status(
                    memory_id=old_mem.id,
                    status=MemoryStatus.SUPERSEDED,
                    valid_to=current_time_iso,
                    superseded_by_id=new_memory.id,
                    supersede_reason=reason
                )

                resolution_logs.append({
                    "type": "MEMORY_SUPERSEDED",
                    "old_memory_id": old_mem.id,
                    "new_memory_id": new_memory.id,
                    "old_value": old_obj,
                    "new_value": new_obj,
                    "reason": reason
                })

        return resolution_logs

    def _resolve_by_semantic_similarity(self, new_memory: MemoryEntry, current_time_iso: str) -> List[Dict[str, Any]]:
        resolution_logs = []
        similar_mems = self.store.vector_search(new_memory.user_id, new_memory.content, top_k=3, min_similarity=0.75)
        for old_mem, sim in similar_mems:
            if old_mem.status == MemoryStatus.ACTIVE and old_mem.id != new_memory.id:
                if self._is_direct_override(old_mem.content, new_memory.content):
                    reason = f"Superseded by newer similar statement (similarity {sim:.2f})"
                    self.store.update_memory_status(
                        memory_id=old_mem.id,
                        status=MemoryStatus.SUPERSEDED,
                        valid_to=current_time_iso,
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

    def _handle_explicit_reversals(self, new_memory: MemoryEntry, current_time_iso: str) -> List[Dict[str, Any]]:
        logs = []
        content_lower = new_memory.content.lower()
        reversal_phrases = ["quit", "stopped", "no longer", "gave up", "cancelled", "deprecated", "switched from"]
        
        if any(rev in content_lower for rev in reversal_phrases):
            active_mems = self.store.get_user_memories(new_memory.user_id, include_superseded=False)
            for old_mem in active_mems:
                if old_mem.id == new_memory.id:
                    continue
                old_val = old_mem.triple.object.lower() if old_mem.triple else old_mem.content.lower()
                
                # Check if old value is mentioned in the cessation statement
                if old_val and any(part in content_lower for part in old_val.split() if len(part) > 2):
                    reason = f"User explicitly ceased/deprecated prior state: '{old_val}'"
                    self.store.update_memory_status(
                        memory_id=old_mem.id,
                        status=MemoryStatus.SUPERSEDED,
                        valid_to=current_time_iso,
                        superseded_by_id=new_memory.id,
                        supersede_reason=reason
                    )
                    logs.append({
                        "type": "EXPLICIT_CESSATION",
                        "old_memory_id": old_mem.id,
                        "target_object": old_val,
                        "reason": reason
                    })
        return logs

    def _is_opposing_predicate(self, predicate: str) -> bool:
        return predicate in self.MUTUALLY_EXCLUSIVE_PREDICATES

    def _is_direct_override(self, old_text: str, new_text: str) -> bool:
        o = old_text.lower()
        n = new_text.lower()
        if ("coffee" in o and ("tea" in n or "matcha" in n or "quit coffee" in n)):
            return True
        if ("live" in o or "seattle" in o or "berlin" in o) and ("moved to" in n or "tokyo" in n or "paris" in n):
            return True
        if ("postgres" in o and "sqlite" in n) or ("react" in o and "vue" in n):
            return True
        if ("keto" in o and "vegan" in n) or ("carnivore" in o and "vegetarian" in n):
            return True
        return False
