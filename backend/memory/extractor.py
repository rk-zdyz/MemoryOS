import re
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from backend.memory.models import MemoryEntry, MemoryType, MemoryStatus, EntityTriple

class MemoryExtractor:
    def __init__(self):
        # High precision semantic regex patterns for structured memory capture
        self.fact_patterns = [
            # Location & Residence
            (r"(?:i live in|i am living in|i moved to|i currently reside in|my home is in|i moved into|my apartment is in)\s+([A-Za-z\s,]+?)(?:\s+(?:last|this|next|since|for)\s+.*|\.|$)", "lives_in", MemoryType.PROFILE_FACT),
            (r"(?:i am from|i'm from|i grew up in)\s+([A-Za-z\s,]+?)(?:\.|$)", "origin_from", MemoryType.PROFILE_FACT),
            
            # Profession & Role & Company
            (r"(?:i work as a|i am a|i'm a|my job is|my role is|i work as an)\s+([A-Za-z\s]+?)(?:\s+at|\s+for|\.|$)", "works_as", MemoryType.PROFILE_FACT),
            (r"(?:i work at|i am employed by|my company is|i joined)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "employed_at", MemoryType.PROFILE_FACT),
            (r"(?:i study|i am a student at|i study computer science at)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "studies_at", MemoryType.PROFILE_FACT),

            # Diet, Health & Allergies
            (r"(?:i am allergic to|i have an allergy to|i'm severely allergic to)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "allergic_to", MemoryType.PROFILE_FACT),
            (r"(?:i follow a|i am on a|i adhere to a|i follow|i am a|i am now a|i turned|i am now|i am strictly|i am strictly a|i switched to a|i eat a|i eat|i became a|i went)\s+(strict vegan|strictly vegan|vegan|strictly vegetarian|vegetarian|pescatarian|heavy keto carnivore|keto carnivore|strict keto|keto|carnivore|paleo|mediterranean)(?:\s+diet)?(?:\s+now)?", "dietary_lifestyle", MemoryType.PROFILE_FACT),
            (r"(?:i gave up\s+[A-Za-z0-9\s]+?\s+and\s+am\s+)(strictly vegan|vegan|vegetarian|strictly vegetarian|pescatarian|keto|carnivore)(?:\s+now)?", "dietary_lifestyle", MemoryType.PROFILE_FACT),
            (r"(?:i don't eat|i quit eating|i avoid eating|i cannot eat|i no longer eat)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "avoids_food", MemoryType.PREFERENCE),
            
            # Beverages & Consumption Preferences
            (r"(?:my favorite beverage is|my favorite drink is|i love drinking|my go-to drink is)\s+([A-Za-z\s]+?)(?:\.|$)", "primary_beverage", MemoryType.PREFERENCE),
            (r"(?:i quit|i stopped drinking|i no longer drink|i gave up)\s+([A-Za-z\s]+?)(?:\s+completely|\.|$)", "stopped_consuming", MemoryType.PREFERENCE),
            (r"(?:now i only drink|i only drink|i switch(?:ed)? to(?: only)?|i drink only)\s+([A-Za-z\s]+?)(?:\.|$)", "primary_beverage", MemoryType.PREFERENCE),
            (r"(?:i prefer|i like|i love|i drink)\s+([A-Za-z\s]+?)(?:\s+over|\s+instead of|\.|$)", "prefers_beverage", MemoryType.PREFERENCE),

            # Technical & Architecture Decisions
            (r"(?:we decided to use|our team is using|we chose|we are building with|we picked|we selected)\s+([A-Za-z0-9\.\-\s]+?)(?:\s+as our primary database|\s+as our database|\s+for|\s+as|\.|$)", "decided_to_use", MemoryType.DECISION),
            (r"(?:we migrated from|we replaced)\s+([A-Za-z0-9\.\-\s]+?)\s+to\s+([A-Za-z0-9\.\-\s]+)", "migrated_tech", MemoryType.DECISION),
            (r"(?:we migrated from|we replaced)\s+([A-Za-z0-9\.\-\s]+?)\s+with\s+([A-Za-z0-9\.\-\s]+)", "migrated_tech", MemoryType.DECISION),
            (r"(?:we cancelled|we scrapped|we deprecated)\s+([A-Za-z0-9\.\-\s]+?)(?:\.|$)", "deprecated_tech", MemoryType.DECISION),
            (r"(?:my favorite ide is|my preferred ide is|i code in|i prefer using)\s+([A-Za-z0-9\s]+?)(?:\.|$)", "prefers_tool", MemoryType.PREFERENCE),
            
            # Contact & Confidential Projects
            (r"(?:my email is|reach me at)\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", "has_email", MemoryType.PROFILE_FACT),
            (r"(?:my phone number is|my number is|call me at|my emergency contact number is)\s+([0-9\-\+\s\(\)]+)", "has_phone", MemoryType.PROFILE_FACT),
            (r"(?:my name is|call me)\s+([A-Za-z]+)(?:\.|$)", "has_name", MemoryType.PROFILE_FACT),
            (r"(?:my secret project is named|my confidential project is codenamed|my confidential project codename is|my secret project is|my confidential project is)\s+([A-Za-z0-9\-_\s]+?)(?:\.|$)", "confidential_project", MemoryType.DECISION),

            # Time-bound Events / Schedules
            (r"(?:i have a meeting with|scheduled a sync with|meeting with)\s+([A-Za-z\s]+?)\s+(?:on|at|this coming|next)\s+([A-Za-z0-9\s:]+)", "has_meeting", MemoryType.EVENT_EPISODE),
            (r"(?:i will be traveling to|visiting|trip to)\s+([A-Za-z\s]+?)\s+(?:on|in|during)\s+([A-Za-z0-9\s]+)", "travel_scheduled", MemoryType.EVENT_EPISODE)
        ]

        # Forgetting / Purge requests
        self.forget_patterns = [
            r"forget\s+(?:that\s+|about\s+|my\s+|the\s+)?(.*)",
            r"delete\s+(?:my\s+|the\s+|what\s+you\s+know\s+about\s+)?(.*)",
            r"remove\s+(?:my\s+|the\s+|the\s+memory\s+of\s+)?(.*)",
            r"erase\s+(?:my\s+|all\s+details\s+about\s+|all\s+memories\s+about\s+)?(.*)",
            r"wipe\s+(?:my\s+|everything\s+about\s+)?(.*)",
            r"never\s+mention\s+(.*)\s+again",
            r"purge\s+(?:my\s+|the\s+)?(.*)"
        ]

    def detect_forget_request(self, text: str) -> Optional[str]:
        text_clean = text.strip().lower().rstrip(".!?")
        for pattern in self.forget_patterns:
            match = re.match(pattern, text_clean, re.IGNORECASE)
            if match:
                target = match.group(1).strip()
                return target if target else "all"
        return None

    def extract_memories(
        self,
        text: str,
        user_id: str = "riku",
        session_id: str = "default",
        simulated_date: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Extracts structured memories from a message."""
        extracted: List[MemoryEntry] = []
        now_iso = simulated_date or datetime.now(timezone.utc).isoformat()
        
        # Check if purely transient query or greeting
        if self._is_transient(text):
            return []

        matched_any = False
        for pattern, predicate, mem_type in self.fact_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                matched_any = True
                groups = m.groups()
                obj = groups[0].strip()
                qualifier = groups[1].strip() if len(groups) > 1 else None
                
                # Clean object string
                obj = re.sub(r'[\.\,\;]$', '', obj).strip()
                
                # Check for special migration pattern where groups are [old, new]
                if predicate == "migrated_tech" and len(groups) >= 2:
                    old_tech = groups[0].strip()
                    new_tech = groups[1].strip()
                    obj = new_tech
                    qualifier = f"migrated from {old_tech}"
                    canonical_predicate = "database_choice" if any(db in text.lower() for db in ["postgres", "sqlite", "mongo", "mysql", "database"]) else "framework_choice"
                else:
                    canonical_predicate = self._canonicalize_predicate(predicate, text, obj)
                
                # Natural memory content
                content = f"User {canonical_predicate.replace('_', ' ')}: {obj}"
                if qualifier:
                    content += f" ({qualifier})"
                
                triple = EntityTriple(
                    subject="User",
                    predicate=canonical_predicate,
                    object=obj,
                    qualifier=qualifier
                )
                
                importance = 0.95 if mem_type in [MemoryType.PROFILE_FACT, MemoryType.DECISION] else 0.75
                if mem_type == MemoryType.EVENT_EPISODE:
                    importance = 0.5
                
                entry = MemoryEntry(
                    user_id=user_id,
                    session_id=session_id,
                    content=content,
                    memory_type=mem_type,
                    status=MemoryStatus.ACTIVE,
                    triple=triple,
                    confidence=0.98,
                    importance=importance,
                    created_at=now_iso,
                    valid_from=now_iso,
                    tags=[canonical_predicate, mem_type.value.lower()]
                )
                extracted.append(entry)

        # Fallback for assertive declarations: "I live...", "I am...", "My..."
        if not matched_any and self._is_assertive_fact(text):
            triple = self._extract_generic_triple(text)
            entry = MemoryEntry(
                user_id=user_id,
                session_id=session_id,
                content=text.strip(),
                memory_type=MemoryType.PROFILE_FACT if "my" in text.lower() else MemoryType.PREFERENCE,
                status=MemoryStatus.ACTIVE,
                triple=triple,
                confidence=0.85,
                importance=0.65,
                created_at=now_iso,
                valid_from=now_iso,
                tags=["user_statement"]
            )
            extracted.append(entry)

        return extracted

    def _canonicalize_predicate(self, predicate: str, raw_text: str, obj_val: str = "") -> str:
        """Maps synonymous predicates to single canonical slots for reliable conflict resolution."""
        raw_lower = raw_text.lower()
        if "moved to" in raw_lower or "live in" in raw_lower or "living in" in raw_lower or "reside" in raw_lower:
            return "lives_in"
        if "coffee" in raw_lower or "tea" in raw_lower or "matcha" in raw_lower or "beverage" in raw_lower or "drink" in raw_lower:
            return "primary_beverage"
        if "diet" in raw_lower or "vegan" in raw_lower or "vegetarian" in raw_lower or "keto" in raw_lower or "carnivore" in raw_lower:
            return "dietary_lifestyle"
        if "database" in raw_lower or "postgres" in raw_lower or "sqlite" in raw_lower or "mongo" in raw_lower or "mysql" in raw_lower:
            return "database_choice"
        if "framework" in raw_lower or "react" in raw_lower or "vue" in raw_lower or "angular" in raw_lower or "next" in raw_lower:
            return "framework_choice"
        if "work as" in raw_lower or "job is" in raw_lower or "role is" in raw_lower:
            return "works_as"
        if "work at" in raw_lower or "employed at" in raw_lower or "company is" in raw_lower:
            return "employed_at"
        if "phone" in raw_lower or "number is" in raw_lower:
            return "has_phone"
        if "secret project" in raw_lower or "confidential project" in raw_lower:
            return "confidential_project"
        return predicate

    def _is_transient(self, text: str) -> bool:
        t = text.strip().lower()
        greetings = [
            "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
            "how are you", "what's up", "yo", "sup", "thanks", "thank you",
            "okay", "ok", "bye", "see ya", "cheers"
        ]
        if t in greetings or t.rstrip("!?.,") in greetings:
            return True
        
        # Query detection
        is_query_start = (
            t.startswith("what ") or t.startswith("where ") or t.startswith("who ") or
            t.startswith("how ") or t.startswith("when ") or t.startswith("why ") or
            t.startswith("can you ") or t.startswith("do you remember") or
            t.startswith("tell me") or t.startswith("which ") or t.startswith("do i ")
        )
        is_fact_override = (
            "i moved" in t or "i changed" in t or "i am now" in t or
            "we migrated" in t or "i quit" in t or "i switched" in t
        )
        if is_query_start and not is_fact_override:
            return True
        return False

    def _is_assertive_fact(self, text: str) -> bool:
        t = text.lower()
        triggers = ["i am ", "i'm ", "my ", "we use ", "we chose ", "i have ", "i live ", "i started ", "i switched ", "we decided "]
        return any(tr in t for tr in triggers) and len(text.split()) >= 3

    def _extract_generic_triple(self, text: str) -> EntityTriple:
        words = text.split()
        return EntityTriple(
            subject="User",
            predicate="stated",
            object=" ".join(words[:6]) + ("..." if len(words) > 6 else "")
        )
