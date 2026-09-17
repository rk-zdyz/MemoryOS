import math
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from backend.memory.models import MemoryEntry, MemoryStatus, MemoryType
from backend.memory.store import MemoryStore

class MemoryDecayManager:
    """
    Manages half-life decay, access reinforcement, and temporal expiration.
    """
    def __init__(self, store: MemoryStore, decay_half_life_days: float = 14.0):
        self.store = store
        self.default_half_life_days = decay_half_life_days

    def compute_retention_score(self, memory: MemoryEntry, reference_time: Optional[datetime] = None) -> float:
        """
        Computes effective retention score S in [0.0, 1.0] using:
        S = importance * 2^(-dt / (half_life * (1 + 0.2 * access_count)))
        """
        if memory.status in [MemoryStatus.SUPERSEDED, MemoryStatus.FORGOTTEN]:
            return 0.0

        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        # Parse last accessed or created time
        try:
            time_str = memory.last_accessed_at or memory.created_at
            mem_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            dt_days = max(0.0, (reference_time - mem_time).total_seconds() / 86400.0)
        except Exception:
            dt_days = 0.0

        # Adjust half-life based on memory type
        if memory.memory_type == MemoryType.PROFILE_FACT:
            effective_half_life = 365.0  # Profile facts persist very long
        elif memory.memory_type == MemoryType.DECISION:
            effective_half_life = 180.0  # Decisions persist long
        elif memory.memory_type == MemoryType.PREFERENCE:
            effective_half_life = 90.0   # Preferences persist moderately
        elif memory.memory_type == MemoryType.EVENT_EPISODE:
            effective_half_life = 7.0    # Events fade after date passes
        else:
            effective_half_life = 2.0    # Transient chit-chat fades very fast

        # Access reinforcement multiplier
        reinforcement = 1.0 + (0.3 * min(memory.access_count, 10))
        half_life = effective_half_life * reinforcement

        # Exponential half-life decay formula
        decay_factor = math.pow(0.5, dt_days / max(half_life, 0.1))
        retention = memory.importance * decay_factor
        return max(0.0, min(1.0, retention))

    def run_lifecycle_pass(self, user_id: str, simulated_current_date: Optional[str] = None) -> List[str]:
        """
        Evaluates all active memories for a user, marking expired events as EXPIRED
        and low-retention transient items as DECAYED.
        """
        ref_time = datetime.now(timezone.utc)
        if simulated_current_date:
            try:
                ref_time = datetime.fromisoformat(simulated_current_date.replace("Z", "+00:00"))
            except Exception:
                pass

        active_memories = self.store.get_user_memories(user_id=user_id, include_superseded=False)
        updated_log = []

        for mem in active_memories:
            # Check for event expiration
            if mem.memory_type == MemoryType.EVENT_EPISODE and mem.triple and mem.triple.qualifier:
                # If event has a past timestamp or date, mark expired
                if "yesterday" in mem.triple.qualifier.lower() or "past" in mem.triple.qualifier.lower():
                    self.store.update_memory_status(mem.id, MemoryStatus.EXPIRED, supersede_reason="Event schedule elapsed")
                    updated_log.append(f"Expired event memory {mem.id}: {mem.content}")
                    continue

            # Check retention score for transient memories
            if mem.memory_type == MemoryType.TRANSIENT:
                score = self.compute_retention_score(mem, ref_time)
                if score < 0.15:
                    self.store.update_memory_status(mem.id, MemoryStatus.DECAYED, supersede_reason=f"Retention score decayed to {score:.2f}")
                    updated_log.append(f"Decayed transient memory {mem.id}: {mem.content}")

        return updated_log
