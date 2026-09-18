import re
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from backend.memory.models import MemoryEntry, MemoryType, MemoryStatus, EntityTriple

class MemoryExtractor:
    def __init__(self):
        # High-coverage semantic regex patterns for structured memory capture
        self.fact_patterns = [
            # Location & Residence
            (
                r"(?:i(?:\s+currently|\s+now)?\s+(?:live|reside|stay|dwell)(?:\s+in|\s+at)?|"
                r"i(?:\'?m| am)\s+(?:currently\s+|now\s+)?(?:living|residing|staying|based|located|settled)(?:\s+in|\s+at)?|"
                r"i(?:\s+just|\s+recently)?\s+(?:moved|relocated)(?:\s+to|\s+into)?|"
                r"my\s+(?:home|apartment|house|place|residence|city|location)\s+is(?:\s+in)?|"
                r"i(?:\'?m| am)\s+(?:currently\s+|now\s+)?in)\s+([A-Za-z\s,]+?)(?:\s+(?:now|currently|right now|lately|recently|today|last\s+\w+|this\s+\w+|since\s+\w+|for\s+\w+)|\.|\!|\?|$)",
                "lives_in",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:i(?:\'?m| am)\s+from|i(?:\'?m| am)\s+originally\s+from|i\s+grew\s+up\s+in|my\s+hometown\s+is)\s+([A-Za-z\s,]+?)(?:\.|\!|\?|$)",
                "origin_from",
                MemoryType.PROFILE_FACT
            ),
            
            # Profession & Role & Company & Education
            (
                r"(?:i(?:\s+currently)?\s+work\s+as\s+(?:a|an)|i(?:\'?m| am)\s+(?:a|an|currently\s+a|currently\s+an)|my\s+job\s+is(?:\s+a|\s+an)?|my\s+role\s+is(?:\s+a|\s+an)?|my\s+title\s+is(?:\s+a|\s+an)?|my\s+profession\s+is(?:\s+a|\s+an)?)\s+([A-Za-z\s]+?)(?:\s+(?:at|for|in|with)\s+[A-Za-z0-9\s]+|\.|\!|\?|$)",
                "works_as",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:i(?:\s+currently)?\s+work\s+(?:at|for|with)|i(?:\'?m| am)\s+(?:employed\s+by|working\s+at|working\s+for|at)|my\s+company\s+is|i(?:\s+just|\s+recently)?\s+joined)\s+([A-Za-z0-9\s]+?)(?:\.|\!|\?|$)",
                "employed_at",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:i(?:\s+currently)?\s+study|i(?:\'?m| am)\s+a\s+student\s+at|i(?:\'?m| am)\s+studying(?:\s+[A-Za-z\s]+)?\s+at)\s+([A-Za-z0-9\s]+?)(?:\.|\!|\?|$)",
                "studies_at",
                MemoryType.PROFILE_FACT
            ),

            # Diet, Health & Allergies
            (
                r"(?:i\s+gave\s+up\s+([A-Za-z0-9\s]+?)\s+and\s+(?:am|i\'m|became|switched\s+to)\s+)(strictly\s+vegan|strict\s+vegan|vegan|strictly\s+vegetarian|strict\s+vegetarian|vegetarian|pescatarian|keto|carnivore|plant-based)",
                "dietary_transition",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:i(?:\'?m| am)\s+(?:severely\s+|deathly\s+)?allergic\s+to|i\s+have\s+(?:an?\s+)?(?:severe\s+)?allergy\s+to|allergic\s+to)\s+([A-Za-z0-9\s]+?)(?:\.|\!|\?|,|$)",
                "allergic_to",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:i(?:\'?m| am)\s+(?:now\s+|a\s+|on\s+a\s+|on\s+|now\s+on\s+a\s+)?|"
                r"i\s+(?:follow|adhere\s+to|turned|switched\s+to|switched\s+to\s+a|became|went|eat|eat\s+a)(?:\s+a|\s+now)?\s+)"
                r"(strict\s+vegan|strictly\s+vegan|vegan|strictly\s+vegetarian|strict\s+vegetarian|vegetarian|pescatarian|heavy\s+keto\s+carnivore|keto\s+carnivore|strict\s+keto|keto|carnivore|paleo|mediterranean|plant-based|gluten-free|dairy-free)"
                r"(?:\s+diet)?(?:\s+now|\s+lately|\s+for\s+health|\.|\!|\?|,|\s+so|\s+and|$)",
                "dietary_lifestyle",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:i\s+(?:don\'t|do\s+not|avoid|cannot|can\'t|no\s+longer)\s+(?:eat|consume|having)|i\s+gave\s+up\s+eating)\s+([A-Za-z0-9\s]+?)(?:\.|\!|\?|,|$)",
                "avoids_food",
                MemoryType.PREFERENCE
            ),
            
            # Beverages & Consumption Preferences
            (
                r"(?:my\s+(?:favorite|favourite|preferred|go-to|daily|usual)\s+(?:beverage|drink)\s+is|"
                r"i(?:\s+really|\s+absolutely)?\s+love\s+drinking|"
                r"i(?:\s+usually|\s+always|\s+mostly|\s+regularly)?\s+drink|"
                r"i(?:\'?m| am)\s+drinking|"
                r"now\s+i(?:\s+only)?\s+drink|"
                r"i\s+only\s+drink|"
                r"i(?:\s+have|\'ve)?\s+switched\s+to(?:\s+only)?|"
                r"i\s+started\s+drinking)\s+([A-Za-z\s]+?)(?:\s+now|\s+these\s+days|\s+lately|\.|\!|\?|,|$)",
                "primary_beverage",
                MemoryType.PREFERENCE
            ),
            (
                r"(?:i\s+(?:quit\s+drinking|quit|stopped\s+drinking|stopped|no\s+longer\s+drink|gave\s+up\s+drinking|gave\s+up))\s+([A-Za-z\s]+?)(?:\s+and\s+|\s+completely|\s+entirely|\.|\!|\?|,|$)",
                "stopped_consuming",
                MemoryType.PREFERENCE
            ),
            (
                r"(?:i\s+prefer|i\s+like|i\s+love)\s+([A-Za-z\s]+?)\s+(?:over|instead\s+of|rather\s+than)\s+([A-Za-z\s]+?)(?:\.|\!|\?|,|$)",
                "prefers_beverage",
                MemoryType.PREFERENCE
            ),

            # Technical & Architecture Decisions
            (
                r"(?:we\s+(?:decided\s+to\s+use|chose|picked|selected|are\s+using|use|built\s+with|are\s+building\s+with|settled\s+on)|"
                r"our\s+(?:team\s+is\s+using|stack\s+is|primary\s+database\s+is|database\s+is|db\s+is|backend\s+is|frontend\s+is))\s+"
                r"([A-Za-z0-9\.\-\s\+]+?)(?:\s+as\s+(?:our|the)\s+(?:primary\s+|main\s+)?(?:database|db|backend|framework|stack|language)|\s+for\s+(?:our|the)\s+[A-Za-z0-9\s]+|\.|\!|\?|$)",
                "decided_to_use",
                MemoryType.DECISION
            ),
            (
                r"(?:we\s+migrated\s+from|we\s+switched\s+from|we\s+moved\s+from|we\s+replaced)\s+([A-Za-z0-9\.\-\s]+?)\s+(?:to|with)\s+([A-Za-z0-9\.\-\s]+)",
                "migrated_tech",
                MemoryType.DECISION
            ),
            (
                r"(?:we\s+cancelled|we\s+scrapped|we\s+deprecated|we\s+dropped|we\s+stopped\s+using)\s+([A-Za-z0-9\.\-\s]+?)(?:\.|\!|\?|$)",
                "deprecated_tech",
                MemoryType.DECISION
            ),
            (
                r"(?:my\s+(?:favorite|favourite|preferred)\s+(?:ide|editor|tool|language)\s+is|"
                r"i\s+(?:code|develop|program)\s+in|"
                r"i\s+prefer\s+using|"
                r"i\s+use\s+(?:the\s+)?(?:ide|editor)\s+)\s*([A-Za-z0-9\.\-\s]+?)(?:\.|\!|\?|$)",
                "prefers_tool",
                MemoryType.PREFERENCE
            ),
            (
                r"(?:i(?:\s+usually|\s+primarily|\s+always)?\s+(?:code\s+in|code\s+with|use))\s+([A-Za-z0-9\.\-\#\+]+)(?:\s+for\s+coding|\s+as\s+my\s+editor|\.|\!|\?|$)",
                "prefers_tool",
                MemoryType.PREFERENCE
            ),
            
            # Contact & Identity & Confidential Projects
            (
                r"(?:my\s+email\s+is|reach\s+me\s+at|contact\s+me\s+at|email\s+me\s+at)\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
                "has_email",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:my\s+(?:phone\s+number|phone|cell\s+phone|cell|mobile|number|emergency\s+contact\s+number)\s+is|call\s+me\s+at)\s+([0-9\-\+\s\(\)]{7,})",
                "has_phone",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:my\s+name\s+is|call\s+me|i(?:\'?m| am)\s+called|the\s+name\s+is)\s+([A-Za-z]+)(?:\.|\!|\?|$)",
                "has_name",
                MemoryType.PROFILE_FACT
            ),
            (
                r"(?:my\s+(?:secret|confidential)\s+project(?:\s+codename)?\s+(?:is\s+named|is\s+codenamed|is|codename\s+is))\s+([A-Za-z0-9\-_\s]+?)(?:\.|\!|\?|$)",
                "confidential_project",
                MemoryType.DECISION
            ),

            # Time-bound Events / Schedules
            (
                r"(?:i\s+have\s+a\s+meeting\s+with|scheduled\s+a\s+sync\s+with|meeting\s+with)\s+([A-Za-z\s]+?)\s+(?:on|at|this\s+coming|next)\s+([A-Za-z0-9\s:]+)",
                "has_meeting",
                MemoryType.EVENT_EPISODE
            ),
            (
                r"(?:i\s+will\s+be\s+traveling\s+to|visiting|trip\s+to)\s+([A-Za-z\s]+?)\s+(?:on|in|during)\s+([A-Za-z0-9\s]+)",
                "travel_scheduled",
                MemoryType.EVENT_EPISODE
            )
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

    def clean_extracted_object(self, obj: str) -> str:
        """Cleans and standardizes extracted object entities."""
        obj = obj.strip(" \t\n\r\"'.,;:!?")
        # Strip leading filler words
        obj = re.sub(r'^(?:a|an|the|to|drinking|eating|consuming)\s+', '', obj, flags=re.IGNORECASE).strip()

        # Strip temporal and contextual filler suffixes
        temporal_suffixes = [
            r"\s+(?:right\s+now|currently|lately|recently|now|today|these\s+days|for\s+now|at\s+the\s+moment)$",
            r"\s+(?:last|this|next)\s+(?:week|month|year|weekend|summer|winter|spring|fall|monday|tuesday|wednesday|thursday|friday|saturday|sunday|decade)$",
            r"\s+since\s+[A-Za-z0-9\s]+$",
            r"\s+for\s+(?:health|work|school|college|fun|good|a\s+while|months|years|days)$",
            r"\s+as\s+(?:our|my|the)\s+(?:primary\s+|main\s+)?(?:database|db|framework|tool|stack|ide|language)$",
            r"\s+for\s+(?:our|my|the)\s+(?:backend|frontend|project|app|database|db|infrastructure|caching)$"
        ]
        for pattern in temporal_suffixes:
            obj = re.sub(pattern, "", obj, flags=re.IGNORECASE).strip(" \t\n\r\"'.,;:!?")

        # Strip trailing punctuation
        obj = re.sub(r'[\.\,\;\:\!\?]+$', '', obj).strip()
        return obj

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
        seen_slots = set()

        for pattern, predicate, mem_type in self.fact_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                matched_any = True
                groups = m.groups()
                raw_obj = groups[0].strip()
                qualifier = groups[1].strip() if len(groups) > 1 else None
                
                # Check for special migration / transition patterns
                if predicate == "migrated_tech" and len(groups) >= 2:
                    old_tech = self.clean_extracted_object(groups[0])
                    new_tech = self.clean_extracted_object(groups[1])
                    obj = new_tech
                    qualifier = f"migrated from {old_tech}"
                    canonical_predicate = "database_choice" if any(db in text.lower() for db in ["postgres", "sqlite", "mongo", "mysql", "database", "db"]) else "framework_choice"
                elif predicate == "dietary_transition" and len(groups) >= 2:
                    old_diet = self.clean_extracted_object(groups[0])
                    new_diet = self.clean_extracted_object(groups[1])
                    obj = new_diet
                    qualifier = f"gave up {old_diet}"
                    canonical_predicate = "dietary_lifestyle"
                else:
                    obj = self.clean_extracted_object(raw_obj)
                    canonical_predicate = self._canonicalize_predicate(predicate, text, obj)
                
                if not obj:
                    continue

                # Deduplicate identical extracted slots from the same text
                slot_key = (canonical_predicate, obj.lower())
                if slot_key in seen_slots:
                    continue
                seen_slots.add(slot_key)
                
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
        obj_lower = obj_val.lower()

        # Location / Residence
        if any(k in raw_lower for k in ["moved to", "live in", "living in", "reside", "stay in", "based in", "located in", "relocated to"]):
            return "lives_in"
        # Beverages
        if any(k in raw_lower or k in obj_lower for k in ["coffee", "tea", "matcha", "beverage", "drink", "cold brew", "latte", "espresso", "soda"]):
            if predicate in ["stopped_consuming", "avoids_food"]:
                return predicate
            return "primary_beverage"
        # Diet
        if any(k in raw_lower or k in obj_lower for k in ["diet", "vegan", "vegetarian", "keto", "carnivore", "paleo", "plant-based", "gluten-free", "dairy-free"]):
            if predicate in ["stopped_consuming", "avoids_food"]:
                return "avoids_food"
            return "dietary_lifestyle"
        # Database
        if any(k in raw_lower or k in obj_lower for k in ["database", "postgres", "sqlite", "mongo", "mysql", "redis", "dynamodb", "supabase", "cassandra"]):
            return "database_choice"
        # Framework
        if any(k in raw_lower or k in obj_lower for k in ["framework", "react", "vue", "angular", "next", "svelte", "django", "fastapi", "express", "graphql"]):
            return "framework_choice"
        # Work / Roles
        if any(k in raw_lower for k in ["work as", "job is", "role is", "profession is", "title is", "engineer", "developer"]):
            return "works_as"
        if any(k in raw_lower for k in ["work at", "employed by", "company is", "joined"]):
            return "employed_at"
        # Contact
        if predicate == "has_phone" or any(k in raw_lower for k in ["phone", "emergency contact number"]):
            return "has_phone"
        # Secret Projects
        if any(k in raw_lower for k in ["secret project", "confidential project"]):
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
            t.startswith("what ") or t.startswith("what's ") or t.startswith("whats ") or
            t.startswith("where ") or t.startswith("where's ") or t.startswith("wheres ") or
            t.startswith("who ") or t.startswith("who's ") or
            t.startswith("how ") or t.startswith("when ") or t.startswith("why ") or
            t.startswith("can you ") or t.startswith("do you remember") or
            t.startswith("tell me") or t.startswith("which ") or t.startswith("do i ") or
            t.startswith("am i ") or t.startswith("should i ") or t.startswith("is my ") or
            t.startswith("are we ") or t.startswith("did we ")
        )
        is_fact_override = (
            "i moved" in t or "i changed" in t or "i am now" in t or
            "we migrated" in t or "i quit" in t or "i switched" in t or
            "i gave up" in t or "i live in" in t or "i reside in" in t or
            "i stay in" in t or "i am in" in t or "i'm in" in t
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
