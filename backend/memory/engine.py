import os
import json
import requests
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from backend.memory.models import (
    MemoryEntry,
    MemoryStatus,
    MemoryType,
    MemoryAttribution,
    MemorySearchResult,
    ChatRequest,
    ChatResponse
)

from backend.memory.store import MemoryStore
from backend.memory.extractor import MemoryExtractor
from backend.memory.conflict_resolver import ConflictResolver
from backend.memory.decay import MemoryDecayManager


class ChronosMemoryEngine:

    def __init__(self, db_path: Optional[str] = None):
        self.store = MemoryStore(db_path=db_path) if db_path else MemoryStore()
        self.extractor = MemoryExtractor()
        self.resolver = ConflictResolver(self.store)
        self.decay_manager = MemoryDecayManager(self.store)

    # ============================================================
    # MAIN CHAT PIPELINE
    # ============================================================

    def process_chat(self, req: ChatRequest) -> ChatResponse:

        user_id = req.user_id
        session_id = req.session_id
        message = req.message
        sim_date = req.simulated_date

        # --------------------------------------------------------
        # 1. Explicit forget / delete / purge command
        # --------------------------------------------------------

        forget_target = self.extractor.detect_forget_request(message)

        if forget_target:
            return self._handle_forget_command(
                user_id,
                session_id,
                message,
                forget_target,
                sim_date
            )

        # --------------------------------------------------------
        # 2. Extract new memories
        # --------------------------------------------------------

        new_extracted = self.extractor.extract_memories(
            text=message,
            user_id=user_id,
            session_id=session_id,
            simulated_date=sim_date
        )

        conflict_notes = []

        for mem in new_extracted:

            # Save new memory
            self.store.save_memory(mem)

            # Resolve contradictions
            resolutions = (
                self.resolver.resolve_conflicts_for_new_memory(
                    mem,
                    simulated_date=sim_date
                )
            )

            for res in resolutions:

                if res.get("reason"):
                    conflict_notes.append(res["reason"])

        # --------------------------------------------------------
        # 3. Lifecycle / decay pass
        # --------------------------------------------------------

        self.decay_manager.run_lifecycle_pass(
            user_id,
            simulated_current_date=sim_date
        )

        # --------------------------------------------------------
        # 4. Retrieve memories
        # --------------------------------------------------------

        search_res = self.retrieve_with_attribution(
            user_id=user_id,
            query=message,
            top_k=6
        )

        # Touch active memories
        for mem in search_res.active_memories:
            self.store.touch_memory(mem.id)

        # --------------------------------------------------------
        # 5. Generate answer
        # --------------------------------------------------------

        answer = self._synthesize_answer(
            query=message,
            search_result=search_res,
            conflict_notes=conflict_notes,
            new_extracted=new_extracted,
            provider=req.provider,
            api_key=req.api_key
        )

        # --------------------------------------------------------
        # 6. Save conversation history
        # --------------------------------------------------------

        used_ids = [
            a.memory_id
            for a in search_res.attributions
            if a.is_active
        ]

        self.store.save_chat_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=message,
            simulated_date=sim_date
        )

        self.store.save_chat_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=answer,
            simulated_date=sim_date,
            memory_ids_used=used_ids
        )

        # --------------------------------------------------------
        # 7. Return structured response
        # --------------------------------------------------------

        active_attributions = [
            a for a in search_res.attributions
            if a.is_active
        ]

        superseded_attributions = [
            a for a in search_res.attributions
            if not a.is_active
        ]

        return ChatResponse(
            answer=answer,
            user_id=user_id,
            session_id=session_id,
            used_memories=active_attributions,
            superseded_memories=superseded_attributions,
            conflict_resolution_notes=conflict_notes,
            new_memories_extracted=new_extracted,
            simulated_date=sim_date
        )

    # ============================================================
    # MEMORY RETRIEVAL + ATTRIBUTION
    # ============================================================

    def retrieve_with_attribution(
        self,
        user_id: str,
        query: str,
        top_k: int = 6
    ) -> MemorySearchResult:

        """
        Retrieves candidate memories using semantic vector search.

        Vector similarity finds candidates, while memory status
        determines whether they are current or historical.
        """

        scored_candidates = self.store.vector_search(
            user_id=user_id,
            query=query,
            top_k=top_k * 2,
            min_similarity=0.15
        )

        active_list: List[MemoryEntry] = []
        superseded_list: List[MemoryEntry] = []
        decayed_list: List[MemoryEntry] = []
        all_retrieved: List[MemoryEntry] = []
        attributions: List[MemoryAttribution] = []

        seen_ids = set()

        for mem, score in scored_candidates:

            if (
                mem.id in seen_ids
                or mem.status == MemoryStatus.FORGOTTEN
            ):
                continue

            seen_ids.add(mem.id)
            all_retrieved.append(mem)

            valid_interval = (
                f"From: "
                f"{mem.valid_from[:10] if mem.valid_from else 'Unknown'}"
            )

            if mem.valid_to:
                valid_interval += (
                    f" -> To: {mem.valid_to[:10]}"
                )
            else:
                valid_interval += " -> Present"

            triple_str = None

            if mem.triple:

                triple_str = (
                    f"({mem.triple.subject} -> "
                    f"{mem.triple.predicate} -> "
                    f"{mem.triple.object})"
                )

            # ----------------------------------------------------
            # ACTIVE
            # ----------------------------------------------------

            if mem.status == MemoryStatus.ACTIVE:

                active_list.append(mem)

                attributions.append(
                    MemoryAttribution(
                        memory_id=mem.id,
                        content=mem.content,
                        memory_type=mem.memory_type,
                        status=mem.status,
                        similarity_score=round(score, 3),
                        confidence=mem.confidence,
                        is_active=True,
                        filter_reason=None,
                        valid_interval=valid_interval,
                        created_at=mem.created_at,
                        triple_repr=triple_str
                    )
                )

            # ----------------------------------------------------
            # SUPERSEDED
            # ----------------------------------------------------

            elif mem.status == MemoryStatus.SUPERSEDED:

                superseded_list.append(mem)

                attributions.append(
                    MemoryAttribution(
                        memory_id=mem.id,
                        content=mem.content,
                        memory_type=mem.memory_type,
                        status=mem.status,
                        similarity_score=round(score, 3),
                        confidence=mem.confidence,
                        is_active=False,
                        filter_reason=(
                            "SUPERSEDED: "
                            f"{mem.supersede_reason or 'Replaced by newer update'}"
                        ),
                        valid_interval=valid_interval,
                        created_at=mem.created_at,
                        triple_repr=triple_str
                    )
                )

            # ----------------------------------------------------
            # DECAYED
            # ----------------------------------------------------

            elif mem.status == MemoryStatus.DECAYED:

                decayed_list.append(mem)

                attributions.append(
                    MemoryAttribution(
                        memory_id=mem.id,
                        content=mem.content,
                        memory_type=mem.memory_type,
                        status=mem.status,
                        similarity_score=round(score, 3),
                        confidence=mem.confidence,
                        is_active=False,
                        filter_reason=(
                            "DECAYED: Relevance decayed over time "
                            "due to inactivity"
                        ),
                        valid_interval=valid_interval,
                        created_at=mem.created_at,
                        triple_repr=triple_str
                    )
                )

            # ----------------------------------------------------
            # EXPIRED
            # ----------------------------------------------------

            elif mem.status == MemoryStatus.EXPIRED:

                attributions.append(
                    MemoryAttribution(
                        memory_id=mem.id,
                        content=mem.content,
                        memory_type=mem.memory_type,
                        status=mem.status,
                        similarity_score=round(score, 3),
                        confidence=mem.confidence,
                        is_active=False,
                        filter_reason=(
                            "EXPIRED: Time-bound schedule/event "
                            "has passed"
                        ),
                        valid_interval=valid_interval,
                        created_at=mem.created_at,
                        triple_repr=triple_str
                    )
                )

        # --------------------------------------------------------
        # Include historical predecessors of active memories
        # --------------------------------------------------------

        for act_mem in list(active_list):

            if not act_mem.triple:
                continue

            related = self.store.find_memories_by_triple(
                user_id=user_id,
                subject=act_mem.triple.subject,
                predicate=act_mem.triple.predicate
            )

            for rel in related:

                if (
                    rel.id not in seen_ids
                    and rel.status == MemoryStatus.SUPERSEDED
                ):

                    seen_ids.add(rel.id)
                    superseded_list.append(rel)

                    valid_interval = (
                        f"From: "
                        f"{rel.valid_from[:10] if rel.valid_from else 'Unknown'}"
                    )

                    if rel.valid_to:
                        valid_interval += (
                            f" -> To: {rel.valid_to[:10]}"
                        )
                    else:
                        valid_interval += " -> Present"

                    triple_str = None

                    if rel.triple:

                        triple_str = (
                            f"({rel.triple.subject} -> "
                            f"{rel.triple.predicate} -> "
                            f"{rel.triple.object})"
                        )

                    attributions.append(
                        MemoryAttribution(
                            memory_id=rel.id,
                            content=rel.content,
                            memory_type=rel.memory_type,
                            status=rel.status,
                            similarity_score=0.95,
                            confidence=rel.confidence,
                            is_active=False,
                            filter_reason=(
                                "SUPERSEDED: "
                                f"{rel.supersede_reason or 'Replaced by newer update'}"
                            ),
                            valid_interval=valid_interval,
                            created_at=rel.created_at,
                            triple_repr=triple_str
                        )
                    )

        return MemorySearchResult(
            active_memories=active_list[:top_k],
            superseded_memories=superseded_list,
            decayed_memories=decayed_list,
            all_retrieved=all_retrieved,
            attributions=attributions,
            conflict_detected=len(superseded_list) > 0,
            conflict_summary=(
                f"Identified {len(superseded_list)} "
                f"superseded historical record(s)"
                if superseded_list
                else None
            )
        )

    # ============================================================
    # ANSWER SYNTHESIS
    # ============================================================

    def _synthesize_answer(
        self,
        query: str,
        search_result: MemorySearchResult,
        conflict_notes: List[str],
        new_extracted: List[MemoryEntry],
        provider: Optional[str] = "local",
        api_key: Optional[str] = None
    ) -> str:

        """
        Generates the final answer.

        Vector search is ONLY used to retrieve candidates.

        Query intent decides which candidate memory is actually
        relevant.

        Historical queries prefer superseded memories.
        Current queries prefer active memories.
        """

        # ========================================================
        # EXTERNAL PROVIDERS
        # ========================================================

        if provider == "gemini" and api_key:

            return self._call_gemini_api(
                query,
                search_result,
                conflict_notes,
                api_key
            )

        elif provider == "openai" and api_key:

            return self._call_openai_api(
                query,
                search_result,
                conflict_notes,
                api_key
            )

        # ========================================================
        # LOCAL SYNTHESIS
        # ========================================================

        active_mems = list(search_result.active_memories)
        superseded_mems = list(
            search_result.superseded_memories
        )

        q = query.lower().strip()

        # ========================================================
        # 1. USER JUST STORED A NEW MEMORY
        # ========================================================

        if new_extracted:

            extracted_summary = ", ".join(
                e.content for e in new_extracted
            )

            if conflict_notes:

                resolution_txt = " | ".join(
                    conflict_notes
                )

                return (
                    f"Got it! I've updated my knowledge: "
                    f"**{extracted_summary}**. "
                    f"({resolution_txt}). "
                    f"I have archived the previous state into "
                    f"your historical timeline."
                )

            return (
                f"I've committed that to memory: "
                f"**{extracted_summary}**."
            )

        # ========================================================
        # 2. DETECT HISTORICAL INTENT
        # ========================================================

        historical_phrases = [
            "previously",
            "before",
            "used to",
            "formerly",
            "old",
            "prior",
            "what was",
            "what were",
            "in the past",
            "back then",
            "earlier"
        ]

        is_historical = any(
            phrase in q
            for phrase in historical_phrases
        )

        # ========================================================
        # 3. HISTORICAL QUESTIONS
        # ========================================================

        if is_historical:

            historical_candidates = []

            # ----------------------------------------------------
            # Location history
            # ----------------------------------------------------

            if (
                "where" in q
                or "live" in q
                or "living" in q
                or "home" in q
            ):

                for mem in superseded_mems:

                    if not mem.triple:
                        continue

                    predicate = (
                        mem.triple.predicate.lower()
                    )

                    if predicate == "lives_in":

                        historical_candidates.append(mem)

            # ----------------------------------------------------
            # Beverage history
            # ----------------------------------------------------

            elif (
                "drink" in q
                or "beverage" in q
            ):

                for mem in superseded_mems:

                    if not mem.triple:
                        continue

                    predicate = (
                        mem.triple.predicate.lower()
                    )

                    if predicate in [
                        "primary_beverage",
                        "prefers_beverage"
                    ]:

                        historical_candidates.append(mem)

            # ----------------------------------------------------
            # Database history
            # ----------------------------------------------------

            elif "database" in q:

                for mem in superseded_mems:

                    if not mem.triple:
                        continue

                    if (
                        mem.triple.predicate.lower()
                        == "database_choice"
                    ):

                        historical_candidates.append(mem)

            # ----------------------------------------------------
            # Framework history
            # ----------------------------------------------------

            elif (
                "framework" in q
                or "technology" in q
                or "tech" in q
                or "stack" in q
            ):

                for mem in superseded_mems:

                    if not mem.triple:
                        continue

                    if (
                        mem.triple.predicate.lower()
                        == "framework_choice"
                    ):

                        historical_candidates.append(mem)

            # ----------------------------------------------------
            # Generic historical fallback
            # ----------------------------------------------------

            if not historical_candidates:

                historical_candidates = list(
                    superseded_mems
                )

            # ----------------------------------------------------
            # Return historical memory
            # ----------------------------------------------------

            if historical_candidates:

                historical_memory = (
                    historical_candidates[0]
                )

                if historical_memory.triple:

                    obj = (
                        historical_memory
                        .triple
                        .object
                    )

                    predicate = (
                        historical_memory
                        .triple
                        .predicate
                        .lower()
                    )

                    if predicate == "lives_in":

                        return (
                            f"Before the current update, "
                            f"you lived in **{obj}**. "
                            f"*(Historical memory: "
                            f"{historical_memory.content}.)*"
                        )

                    return (
                        f"Previously, your memory was "
                        f"**{obj}**. "
                        f"*(Historical memory: "
                        f"{historical_memory.content}.)*"
                    )

                return (
                    f"I found a historical memory: "
                    f"**{historical_memory.content}**."
                )

            # No historical memory found

            return (
                "I don't have a relevant historical memory "
                "for that."
            )

        # ========================================================
        # 4. CURRENT LOCATION
        # ========================================================

        if any(x in q for x in [
            "where do i live",
            "where am i living",
            "where is my home",
            "where do you think i live",
            "where do i currently live",
            "where am i located",
            "where's my home"
        ]):

            relevant = []

            for mem in active_mems:

                if not mem.triple:
                    continue

                predicate = (
                    mem.triple.predicate.lower()
                )

                if predicate == "lives_in":
                    relevant.append(mem)

            if relevant:

                mem = relevant[0]

                obj = mem.triple.object

                return (
                    f"Based on my memory, "
                    f"you live in **{obj}**."
                )

            return (
                "I don't have a recorded current "
                "location for you."
            )

        # ========================================================
        # 5. CURRENT BEVERAGE
        # ========================================================

        if any(x in q for x in [
            "favorite beverage",
            "favourite beverage",
            "favorite drink",
            "favourite drink",
            "what do i drink",
            "what beverage do i",
            "what drink do i",
            "which beverage do i",
            "which drink do i",
            "do i drink"
        ]):

            relevant = []

            for mem in active_mems:

                if not mem.triple:
                    continue

                predicate = (
                    mem.triple.predicate.lower()
                )

                if predicate in [
                    "primary_beverage",
                    "prefers_beverage"
                ]:

                    relevant.append(mem)

            if relevant:

                mem = relevant[0]

                obj = mem.triple.object

                return (
                    f"Based on my memory, "
                    f"your preferred beverage is "
                    f"**{obj}**."
                )

            return (
                "I don't have a recorded beverage "
                "preference for you."
            )

        # ========================================================
        # 6. CURRENT DATABASE
        # ========================================================

        if any(x in q for x in [
            "what database",
            "which database",
            "database did we",
            "database are we",
            "database do we use",
            "what db",
            "which db"
        ]):

            relevant = []

            for mem in active_mems:

                if not mem.triple:
                    continue

                predicate = (
                    mem.triple.predicate.lower()
                )

                if predicate == "database_choice":

                    relevant.append(mem)

            if relevant:

                mem = relevant[0]

                obj = mem.triple.object

                return (
                    f"Based on my memory, "
                    f"we chose **{obj}** as the database."
                )

            return (
                "I don't have a recorded database "
                "decision for the project."
            )

        # ========================================================
        # 7. CURRENT FRAMEWORK / TECHNOLOGY
        # ========================================================

        if any(x in q for x in [
            "what framework",
            "which framework",
            "what technology",
            "which technology",
            "what tech",
            "which tech",
            "what stack",
            "which stack"
        ]):

            relevant = []

            for mem in active_mems:

                if not mem.triple:
                    continue

                predicate = (
                    mem.triple.predicate.lower()
                )

                if predicate == "framework_choice":

                    relevant.append(mem)

            if relevant:

                mem = relevant[0]

                obj = mem.triple.object

                return (
                    f"Based on my memory, "
                    f"the project uses **{obj}**."
                )

            return (
                "I don't have a recorded framework "
                "or technology choice for that."
            )

        # ========================================================
        # 8. NAME
        # ========================================================

        if any(x in q for x in [
            "what is my name",
            "what's my name",
            "who am i",
            "what should you call me",
            "what do you call me"
        ]):

            relevant = []

            for mem in active_mems:

                if not mem.triple:
                    continue

                predicate = (
                    mem.triple.predicate.lower()
                )

                if predicate == "has_name":

                    relevant.append(mem)

            if relevant:

                mem = relevant[0]

                obj = mem.triple.object

                return (
                    f"Based on my memory, "
                    f"your name is **{obj}**."
                )

            return (
                "I don't have your name recorded yet."
            )

        # ========================================================
        # 9. JOB / ROLE
        # ========================================================

        if any(x in q for x in [
            "what is my job",
            "what do i do",
            "where do i work",
            "what is my role",
            "what's my role",
            "what profession",
            "what do i work as"
        ]):

            relevant = []

            for mem in active_mems:

                if not mem.triple:
                    continue

                predicate = (
                    mem.triple.predicate.lower()
                )

                if predicate in [
                    "works_as",
                    "employed_at"
                ]:

                    relevant.append(mem)

            if relevant:

                mem = relevant[0]

                obj = mem.triple.object

                return (
                    f"Based on my memory, "
                    f"you are associated with **{obj}**."
                )

            return (
                "I don't have your current job or role "
                "recorded yet."
            )

        # ========================================================
        # 10. DIET
        # ========================================================

        if any(x in q for x in [
            "what is my diet",
            "what do i eat",
            "what can i eat",
            "am i vegan",
            "am i vegetarian",
            "what is my dietary"
        ]):

            relevant = []

            for mem in active_mems:

                if not mem.triple:
                    continue

                predicate = (
                    mem.triple.predicate.lower()
                )

                if predicate in [
                    "dietary_lifestyle",
                    "avoids_food"
                ]:

                    relevant.append(mem)

            if relevant:

                mem = relevant[0]

                obj = mem.triple.object

                return (
                    f"Based on my memory, "
                    f"your dietary information is "
                    f"**{obj}**."
                )

            return (
                "I don't have your dietary information "
                "recorded yet."
            )

        # ========================================================
        # 11. GENERIC QUESTION
        # ========================================================

        if "?" in q:

            # CRITICAL:
            #
            # Never blindly use active_mems[0].
            #
            # If the question does not match a known memory
            # intent, unrelated memories are rejected.

            return (
                "I don't have any recorded memories "
                "regarding that yet."
            )

        # ========================================================
        # 12. NON-QUESTION
        # ========================================================

        if active_mems:

            top_active = active_mems[0]

            main_fact = top_active.content

            if top_active.triple:

                subject = (
                    top_active.triple.subject
                )

                predicate = (
                    top_active.triple.predicate
                    .replace("_", " ")
                )

                obj = (
                    top_active.triple.object
                )

                qualifier = ""

                if top_active.triple.qualifier:

                    qualifier = (
                        f" ({top_active.triple.qualifier})"
                    )

                main_fact = (
                    f"{subject} {predicate} "
                    f"**{obj}**{qualifier}"
                )

            return (
                f"Based on my memory, "
                f"{main_fact}."
            )

        # ========================================================
        # 13. NOTHING FOUND
        # ========================================================

        return (
            "I don't have any recorded memories "
            "regarding that yet. You can tell me your "
            "preferences, decisions, or details anytime "
            "and I will remember them across sessions!"
        )

    # ============================================================
    # FORGET / GDPR
    # ============================================================

    def _handle_forget_command(
        self,
        user_id: str,
        session_id: str,
        raw_message: str,
        forget_target: str,
        sim_date: Optional[str]
    ) -> ChatResponse:

        candidates = self.store.vector_search(
            user_id=user_id,
            query=forget_target,
            top_k=5,
            min_similarity=0.2
        )

        forgotten_count = 0
        details = []

        for mem, score in candidates:

            if mem.status != MemoryStatus.FORGOTTEN:

                self.store.forget_memory(
                    memory_id=mem.id,
                    user_id=user_id,
                    reason=(
                        f"User instructed to forget: "
                        f"'{forget_target}'"
                    )
                )

                forgotten_count += 1

                details.append(
                    f"Purged memory ID #{mem.id[:8]} "
                    f"({mem.memory_type.value})"
                )

        # --------------------------------------------------------
        # Fallback keyword matching
        # --------------------------------------------------------

        if forgotten_count == 0:

            all_mems = self.store.get_user_memories(
                user_id=user_id,
                include_superseded=True
            )

            for mem in all_mems:

                if any(
                    word.lower() in mem.content.lower()
                    for word in forget_target.split()
                    if len(word) > 2
                ):

                    self.store.forget_memory(
                        mem.id,
                        user_id=user_id,
                        reason=(
                            f"Keyword match purge: "
                            f"'{forget_target}'"
                        )
                    )

                    forgotten_count += 1

                    details.append(
                        f"Purged memory ID #{mem.id[:8]}"
                    )

        answer = (
            f"I have purged {forgotten_count} memory record(s) "
            f"matching '{forget_target}'. "
            f"An immutable audit log entry has been generated, "
            f"and this information will never be recalled."
        )

        self.store.save_chat_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=raw_message,
            simulated_date=sim_date
        )

        self.store.save_chat_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=answer,
            simulated_date=sim_date
        )

        return ChatResponse(
            answer=answer,
            user_id=user_id,
            session_id=session_id,
            used_memories=[],
            superseded_memories=[],
            conflict_resolution_notes=[
                f"GDPR Purge executed: "
                f"{forgotten_count} records erased."
            ],
            new_memories_extracted=[],
            simulated_date=sim_date
        )

    # ============================================================
    # GEMINI
    # ============================================================

    def _call_gemini_api(
        self,
        query: str,
        search_res: MemorySearchResult,
        conflict_notes: List[str],
        api_key: str
    ) -> str:

        try:

            url = (
                "https://generativelanguage.googleapis.com/"
                "v1beta/models/gemini-1.5-flash:"
                f"generateContent?key={api_key}"
            )

            context = "\n".join(
                [
                    f"- [ACTIVE MEMORY #{m.id[:6]}]: "
                    f"{m.content}"
                    for m in search_res.active_memories
                ]
            )

            if search_res.superseded_memories:

                context += "\n" + "\n".join(
                    [
                        f"- [HISTORICAL SUPERSEDED "
                        f"#{m.id[:6]} - DO NOT USE AS CURRENT "
                        f"TRUTH]: {m.content} "
                        f"(Reason: {m.supersede_reason})"
                        for m in search_res.superseded_memories
                    ]
                )

            prompt = f"""
System:
You are MemoryOS, an AI assistant with strict
temporal memory.

Rules:
1. Answer the user's actual question.
2. Use only relevant active memories for current facts.
3. Do not use unrelated memories.
4. Superseded memories represent historical information.
5. If the user explicitly asks about the past, historical
   memories may be used.
6. If no relevant memory exists, say so.
7. Do not invent memories.
8. Explain the memory used when appropriate.

Memory Context:
{context}

User Question:
{query}
"""

            resp = requests.post(
                url,
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
                timeout=10
            )

            data = resp.json()

            return (
                data["candidates"][0]
                ["content"]["parts"][0]["text"]
            )

        except Exception:

            return self._synthesize_answer(
                query=query,
                search_result=search_res,
                conflict_notes=conflict_notes,
                new_extracted=[],
                provider="local"
            )

    # ============================================================
    # OPENAI
    # ============================================================

    def _call_openai_api(
        self,
        query: str,
        search_res: MemorySearchResult,
        conflict_notes: List[str],
        api_key: str
    ) -> str:

        try:

            url = "https://api.openai.com/v1/chat/completions"

            context = "\n".join(
                [
                    f"- [ACTIVE MEMORY #{m.id[:6]}]: "
                    f"{m.content}"
                    for m in search_res.active_memories
                ]
            )

            if search_res.superseded_memories:

                context += "\n" + "\n".join(
                    [
                        f"- [HISTORICAL SUPERSEDED "
                        f"#{m.id[:6]}]: {m.content} "
                        f"(Reason: {m.supersede_reason})"
                        for m in search_res.superseded_memories
                    ]
                )

            system_prompt = """
You are MemoryOS, an AI assistant with persistent
temporal memory.

Rules:
- Answer the actual user question.
- Use only relevant active memories for current facts.
- Never use unrelated memories just because vector
  similarity is high.
- Superseded memories are historical.
- If the user asks about previous or old information,
  historical memories may be used.
- Never invent information.
- If no relevant memory exists, say so.
"""

            user_prompt = f"""
Memory Context:

{context}

User Question:

{query}
"""

            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    "temperature": 0.2
                },
                timeout=15
            )

            data = response.json()

            return (
                data["choices"][0]
                ["message"]["content"]
            )

        except Exception:

            return self._synthesize_answer(
                query=query,
                search_result=search_res,
                conflict_notes=conflict_notes,
                new_extracted=[],
                provider="local"
            )

    # ============================================================
    # KNOWLEDGE GRAPH
    # ============================================================

    def get_knowledge_graph(
        self,
        user_id: str
    ) -> Dict[str, Any]:

        """
        Generates node and edge data for the
        Knowledge Graph visualization.
        """

        memories = self.store.get_user_memories(
            user_id=user_id,
            include_superseded=True,
            include_forgotten=False
        )

        nodes = []
        edges = []

        # --------------------------------------------------------
        # Central User Node
        # --------------------------------------------------------

        user_node_id = f"user_{user_id}"

        nodes.append({
            "id": user_node_id,
            "label": f"User: {user_id.capitalize()}",
            "type": "USER",
            "status": "ACTIVE",
            "color": "#6366f1"
        })

        node_ids = {
            user_node_id
        }

        # --------------------------------------------------------
        # Memory Nodes
        # --------------------------------------------------------

        for mem in memories:

            mem_node_id = f"mem_{mem.id[:8]}"

            label = (
                mem.triple.object
                if mem.triple
                else mem.content[:24]
            )

            if mem.status == MemoryStatus.ACTIVE:

                status_color = "#10b981"

            elif mem.status == MemoryStatus.SUPERSEDED:

                status_color = "#f59e0b"

            else:

                status_color = "#6b7280"

            nodes.append({
                "id": mem_node_id,
                "label": label,
                "full_content": mem.content,
                "type": mem.memory_type.value,
                "status": mem.status.value,
                "color": status_color,
                "confidence": mem.confidence,
                "valid_interval": (
                    f"{mem.valid_from[:10] if mem.valid_from else ''}"
                    f" -> "
                    f"{mem.valid_to[:10] if mem.valid_to else 'Now'}"
                ),
                "supersede_reason": mem.supersede_reason
            })

            node_ids.add(mem_node_id)

            # ----------------------------------------------------
            # User -> Memory
            # ----------------------------------------------------

            rel_label = (
                mem.triple.predicate.replace("_", " ")
                if mem.triple
                else "stated"
            )

            edges.append({
                "id": f"e_{user_node_id}_{mem_node_id}",
                "source": user_node_id,
                "target": mem_node_id,
                "label": rel_label,
                "status": mem.status.value,
                "is_dashed": (
                    mem.status != MemoryStatus.ACTIVE
                )
            })

            # ----------------------------------------------------
            # Memory Evolution Link
            # ----------------------------------------------------

            if mem.superseded_by_id:

                target_mem_id = (
                    f"mem_{mem.superseded_by_id[:8]}"
                )

                edges.append({
                    "id": (
                        f"evol_{mem_node_id}_"
                        f"{target_mem_id}"
                    ),
                    "source": mem_node_id,
                    "target": target_mem_id,
                    "label": "mutated_to",
                    "status": "EVOLUTION",
                    "color": "#ef4444",
                    "is_dashed": True
                })

        return {
            "nodes": nodes,
            "edges": edges
        }

    # ============================================================
    # TIMELINE
    # ============================================================

    def get_timeline_events(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:

        """
        Generates a sorted chronological timeline of
        memory state transitions.
        """

        memories = self.store.get_user_memories(
            user_id=user_id,
            include_superseded=True,
            include_forgotten=True
        )

        events = []

        for mem in memories:

            events.append({
                "id": mem.id,
                "content": mem.content,
                "memory_type": mem.memory_type.value,
                "status": mem.status.value,
                "created_at": mem.created_at,
                "valid_from": mem.valid_from,
                "valid_to": mem.valid_to,
                "superseded_by_id": mem.superseded_by_id,
                "supersede_reason": mem.supersede_reason,
                "triple": (
                    mem.triple.dict()
                    if mem.triple
                    else None
                )
            })

        events.sort(
            key=lambda x: x["created_at"]
        )

        return events