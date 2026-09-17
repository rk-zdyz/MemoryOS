import re
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from backend.memory.models import MemoryEntry, MemoryType, MemoryStatus, EntityTriple

class MemoryExtractor:
    def __init__(self):
        # High precision semantic regex patterns for facts and preferences
        self.fact_patterns = [
            # Location & Residence
            (r"(?:i live in|i am living in|i moved to|i currently reside in|my home is in)\s+([A-Za-z\s,]+)", "lives_in", MemoryType.PROFILE_FACT),
            (r"(?:i am from|i'm from|i grew up in)\s+([A-Za-z\s,]+)", "origin_from", MemoryType.PROFILE_FACT),
            
            # Profession & Role
            (r"(?:i work as a|i am a|i'm a|my job is|my role is)\s+([A-Za-z\s]+?)(?:at|\.|$)", "works_as", MemoryType.PROFILE_FACT),
            (r"(?:i work at|i am employed by|my company is)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "employed_at", MemoryType.PROFILE_FACT),
            
            # Diet & Health & Allergies
            (r"(?:i am allergic to|i have an allergy to)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "allergic_to", MemoryType.PROFILE_FACT),
            (r"(?:i am a|i am now|i turned)\s+(vegan|vegetarian|pescatarian|keto|carnivore)", "dietary_lifestyle", MemoryType.PROFILE_FACT),
            (r"(?:i don't eat|i quit eating|i avoid eating|i cannot eat)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "avoids_food", MemoryType.PREFERENCE),
            
            # Beverages & Preferences
            (r"(?:i prefer|i like|i love|i drink|my favorite beverage is)\s+([A-Za-z\s]+?)(?:over|instead of|\.|$)", "prefers_beverage", MemoryType.PREFERENCE),
            (r"(?:i quit|i stopped drinking|i no longer drink|i gave up)\s+([A-Za-z\s]+?)(?:\.|$)", "stopped_consuming", MemoryType.PREFERENCE),
            (r"(?:i switch(?:ed)? to|now i only drink|i only drink)\s+([A-Za-z\s]+?)(?:\.|$)", "prefers_beverage", MemoryType.PREFERENCE),
            
            # Technical & Project Decisions
            (r"(?:we decided to use|our team is using|we chose|we are building with|we picked)\s+([A-Za-z0-9\.\s]+?)(?:for|as|\.|$)", "decided_to_use", MemoryType.DECISION),
            (r"(?:we migrated from|we replaced)\s+([A-Za-z0-9\.\s]+?)\s+with\s+([A-Za-z0-9\.\s]+)", "migrated_tech", MemoryType.DECISION),
            (r"(?:we cancelled|we scrapped|we deprecated)\s+([A-Za-z0-9\.\s]+?)(?:\.|$)", "deprecated_tech", MemoryType.DECISION),
            (r"(?:my favorite ide is|i code in|i prefer using)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "prefers_tool", MemoryType.PREFERENCE),
            
            # Contact & Identification
            (r"(?:my email is|reach me at)\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", "has_email", MemoryType.PROFILE_FACT),
            (r"(?:my phone number is|my number is|call me at)\s+([0-9\-\+\s\(\)]+)", "has_phone", MemoryType.PROFILE_FACT),
            (r"(?:my name is|call me|i am)\s+([A-Za-z]+)(?:\.|$)", "has_name", MemoryType.PROFILE_FACT),
            
            # Time-bound Events / Meetings
            (r"(?:i have a meeting with|scheduled a sync with|meeting)\s+([A-Za-z\s]+)\s+(?:on|at|this coming|next)\s+([A-Za-z0-9\s:]+)", "has_meeting", MemoryType.EVENT_EPISODE),
            (r"(?:i will be traveling to|visiting|trip to)\s+([A-Za-z\s]+)\s+(?:on|in|during)\s+([A-Za-z0-9\s]+)", "travel_scheduled", MemoryType.EVENT_EPISODE)
        ]

        # Forgetting / Purge requests
        self.forget_patterns = [
            r"forget\s+(?:that\s+|about\s+|my\s+|the\s+)?(.*)",
            r"delete\s+(?:my\s+|the\s+|what\s+you\s+know\s+about\s+)?(.*)",
            r"remove\s+(?:my\s+|the\s+|the\s+memory\s+of\s+)?(.*)",
            r"erase\s+(?:my\s+|all\s+details\s+about\s+|all\s+memories\s+about\s+)?(.*)",
            r"wipe\s+(?:my\s+|everything\s+about\s+)?(.*)",
            r"never\s+mention\s+(.*)\s+again"
        ]

    def detect_forget_request(self, text: str) -> Optional[str]:
        text_clean = text.strip().lower().rstrip(".!?")
        for pattern in self.forget_patterns:
            match = re.match(pattern, text_clean, re.IGNORECASE)
            if match:
                target = match.group(1).strip()
                return target if target else "all"
        return None

    def extract_memories(self, text: str, user_id: str = "alice", session_id: str = "default", simulated_date: Optional[str] = None) -> List[MemoryEntry]:
        """Extracts structured memories from a message"""
        extracted = []
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Check if this is a transient greeting or conversational filler
        if self._is_transient(text):
            return []

        # Try regex patterns
        matched_any = False
        for pattern, predicate, mem_type in self.fact_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                matched_any = True
                groups = m.groups()
                obj = groups[0].strip()
                qualifier = groups[1].strip() if len(groups) > 1 else (simulated_date or None)
                
                # Clean object string
                obj = re.sub(r'[\.\,\;]$', '', obj).strip()
                
                # Canonicalize predicates for conflict detection
                canonical_predicate = self._canonicalize_predicate(predicate, text)
                
                # Formulate natural memory content
                content = f"User {canonical_predicate.replace('_', ' ')}: {obj}"
                if qualifier:
                    content += f" ({qualifier})"
                
                triple = EntityTriple(
                    subject="User",
                    predicate=canonical_predicate,
                    object=obj,
                    qualifier=qualifier
                )
                
                importance = 0.9 if mem_type in [MemoryType.PROFILE_FACT, MemoryType.DECISION] else 0.7
                if mem_type == MemoryType.EVENT_EPISODE:
                    importance = 0.5
                
                entry = MemoryEntry(
                    user_id=user_id,
                    session_id=session_id,
                    content=content,
                    memory_type=mem_type,
                    status=MemoryStatus.ACTIVE,
                    triple=triple,
                    confidence=0.95,
                    importance=importance,
                    created_at=now_iso,
                    valid_from=simulated_date or now_iso,
                    tags=[canonical_predicate, mem_type.value.lower()]
                )
                extracted.append(entry)

        # Fallback for statements expressing definitive facts: "I...", "My..."
        if not matched_any and self._is_assertive_fact(text):
            triple = self._extract_generic_triple(text)
            entry = MemoryEntry(
                user_id=user_id,
                session_id=session_id,
                content=text.strip(),
                memory_type=MemoryType.PROFILE_FACT if "my" in text.lower() else MemoryType.PREFERENCE,
                status=MemoryStatus.ACTIVE,
                triple=triple,
                confidence=0.8,
                importance=0.6,
                created_at=now_iso,
                valid_from=simulated_date or now_iso,
                tags=["user_statement"]
            )
            extracted.append(entry)

        return extracted

    def _canonicalize_predicate(self, predicate: str, raw_text: str) -> str:
        """Groups equivalent predicates so contradictory values map to the same slot"""
        raw_lower = raw_text.lower()
        if "moved to" in raw_lower or "live in" in raw_lower or "living in" in raw_lower or "reside in" in raw_lower:
            return "lives_in"
        if "coffee" in raw_lower or "tea" in raw_lower or "beverage" in raw_lower or "drink" in raw_lower:
            return "primary_beverage"
        if "diet" in raw_lower or "vegan" in raw_lower or "vegetarian" in raw_lower or "keto" in raw_lower:
            return "dietary_lifestyle"
        if "database" in raw_lower or "postgresql" in raw_lower or "mongodb" in raw_lower or "mysql" in raw_lower or "sqlite" in raw_lower:
            return "database_choice"
        if "framework" in raw_lower or "react" in raw_lower or "vue" in raw_lower or "angular" in raw_lower or "next" in raw_lower:
            return "framework_choice"
        return predicate

    def _is_transient(self, text: str) -> bool:
        t = text.strip().lower()
        # Pure queries or pure greetings
        greetings = ["hi", "hello", "hey", "good morning", "good evening", "how are you", "what's up", "yo", "sup", "thanks", "thank you", "okay", "bye", "see ya"]
        if t in greetings or t.rstrip("!?.,") in greetings:
            return True
        if (t.startswith("what ") or t.startswith("where ") or t.startswith("who ") or t.startswith("how ") or t.startswith("when ") or t.startswith("why ") or t.startswith("can you ") or t.startswith("do you remember") or t.startswith("tell me")) and not ("i moved" in t or "i changed" in t or "i am now" in t):
            # It's a query, not a fact declaration
            return True
        return False

    def _is_assertive_fact(self, text: str) -> bool:
        t = text.lower()
        assertive_triggers = ["i am", "i'm", "my ", "we use", "we chose", "i have", "i live", "i started", "i switched"]
        return any(tr in t for tr in assertive_triggers) and len(text.split()) > 2

    def _extract_generic_triple(self, text: str) -> EntityTriple:
        words = text.split()
        return EntityTriple(
            subject="User",
            predicate="stated",
            object=" ".join(words[:6]) + "..." if len(words) > 6 else text
        )
