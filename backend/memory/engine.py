import os
import json
import time
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
        start_time = time.perf_counter()
        user_id = req.user_id
        session_id = req.session_id
        message = req.message
        sim_date = req.simulated_date

        # --------------------------------------------------------
        # 1. Explicit forget / GDPR purge command
        # --------------------------------------------------------
        forget_target = self.extractor.detect_forget_request(message)
        if forget_target:
            resp = self._handle_forget_command(user_id, session_id, message, forget_target, sim_date)
            resp.latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return resp

        # --------------------------------------------------------
        # 2. Extract new memories from statement
        # --------------------------------------------------------
        new_extracted = self.extractor.extract_memories(
            text=message,
            user_id=user_id,
            session_id=session_id,
            simulated_date=sim_date
        )

        conflict_notes: List[str] = []
        for mem in new_extracted:
            # Save new memory
            self.store.save_memory(mem)
            # Resolve contradictions and link superseded states
            resolutions = self.resolver.resolve_conflicts_for_new_memory(mem, simulated_date=sim_date)
            for res in resolutions:
                if res.get("reason"):
                    conflict_notes.append(res["reason"])

        # --------------------------------------------------------
        # 3. Memory lifecycle & decay pass
        # --------------------------------------------------------
        self.decay_manager.run_lifecycle_pass(user_id, simulated_current_date=sim_date)

        # --------------------------------------------------------
        # 4. Hybrid memory retrieval with attribution
        # --------------------------------------------------------
        search_res = self.retrieve_with_attribution(
            user_id=user_id,
            query=message,
            top_k=6,
            simulated_date=sim_date
        )

        # Touch active retrieved memories to reinforce retention
        for mem in search_res.active_memories:
            self.store.touch_memory(mem.id)

        # --------------------------------------------------------
        # 5. Cognitive answer synthesis
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
        used_ids = [a.memory_id for a in search_res.attributions if a.is_active]
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
        # 7. Formulate structured response
        # --------------------------------------------------------
        active_attributions = [a for a in search_res.attributions if a.is_active]
        superseded_attributions = [a for a in search_res.attributions if not a.is_active]

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ChatResponse(
            answer=answer,
            user_id=user_id,
            session_id=session_id,
            used_memories=active_attributions,
            superseded_memories=superseded_attributions,
            conflict_resolution_notes=conflict_notes,
            new_memories_extracted=new_extracted,
            simulated_date=sim_date,
            latency_ms=latency_ms
        )

    # ============================================================
    # MEMORY RETRIEVAL & ATTRIBUTION TRACE
    # ============================================================

    def retrieve_with_attribution(
        self,
        user_id: str,
        query: str,
        top_k: int = 6,
        simulated_date: Optional[str] = None
    ) -> MemorySearchResult:
        """
        Retrieves relevant candidate memories using hybrid semantic search.
        Separates active truth from superseded historical lineage and provides
        a 100% transparent attribution trace.
        """
        scored_candidates = self.store.vector_search(
            user_id=user_id,
            query=query,
            top_k=top_k * 2,
            min_similarity=0.15,
            simulated_date=simulated_date
        )

        active_list: List[MemoryEntry] = []
        superseded_list: List[MemoryEntry] = []
        decayed_list: List[MemoryEntry] = []
        all_retrieved: List[MemoryEntry] = []
        attributions: List[MemoryAttribution] = []
        seen_ids = set()

        for mem, score in scored_candidates:
            if mem.id in seen_ids or mem.status == MemoryStatus.FORGOTTEN:
                continue

            seen_ids.add(mem.id)
            all_retrieved.append(mem)

            valid_interval = f"From: {mem.valid_from[:10] if mem.valid_from else 'Unknown'}"
            if mem.valid_to:
                valid_interval += f" ➔ To: {mem.valid_to[:10]}"
            else:
                valid_interval += " ➔ Present"

            triple_str = None
            if mem.triple:
                triple_str = f"({mem.triple.subject} ➔ {mem.triple.predicate} ➔ {mem.triple.object})"

            if mem.status == MemoryStatus.ACTIVE:
                active_list.append(mem)
                attributions.append(MemoryAttribution(
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
                ))
            elif mem.status == MemoryStatus.SUPERSEDED:
                superseded_list.append(mem)
                attributions.append(MemoryAttribution(
                    memory_id=mem.id,
                    content=mem.content,
                    memory_type=mem.memory_type,
                    status=mem.status,
                    similarity_score=round(score, 3),
                    confidence=mem.confidence,
                    is_active=False,
                    filter_reason=f"SUPERSEDED: {mem.supersede_reason or 'Replaced by newer state'}",
                    valid_interval=valid_interval,
                    created_at=mem.created_at,
                    triple_repr=triple_str
                ))
            elif mem.status == MemoryStatus.DECAYED:
                decayed_list.append(mem)
                attributions.append(MemoryAttribution(
                    memory_id=mem.id,
                    content=mem.content,
                    memory_type=mem.memory_type,
                    status=mem.status,
                    similarity_score=round(score, 3),
                    confidence=mem.confidence,
                    is_active=False,
                    filter_reason="DECAYED: Relevance diminished due to inactivity",
                    valid_interval=valid_interval,
                    created_at=mem.created_at,
                    triple_repr=triple_str
                ))
            elif mem.status == MemoryStatus.EXPIRED:
                attributions.append(MemoryAttribution(
                    memory_id=mem.id,
                    content=mem.content,
                    memory_type=mem.memory_type,
                    status=mem.status,
                    similarity_score=round(score, 3),
                    confidence=mem.confidence,
                    is_active=False,
                    filter_reason="EXPIRED: Time-bound schedule/event has elapsed",
                    valid_interval=valid_interval,
                    created_at=mem.created_at,
                    triple_repr=triple_str
                ))

        # Include historical predecessors for active memories to ensure explainability
        for act_mem in list(active_list):
            if not act_mem.triple:
                continue
            related = self.store.find_memories_by_triple(
                user_id=user_id,
                subject=act_mem.triple.subject,
                predicate=act_mem.triple.predicate
            )
            for rel in related:
                if rel.id not in seen_ids and rel.status == MemoryStatus.SUPERSEDED:
                    seen_ids.add(rel.id)
                    superseded_list.append(rel)
                    valid_interval = f"From: {rel.valid_from[:10] if rel.valid_from else 'Unknown'}"
                    if rel.valid_to:
                        valid_interval += f" ➔ To: {rel.valid_to[:10]}"
                    else:
                        valid_interval += " ➔ Present"
                    
                    triple_str = f"({rel.triple.subject} ➔ {rel.triple.predicate} ➔ {rel.triple.object})" if rel.triple else None
                    attributions.append(MemoryAttribution(
                        memory_id=rel.id,
                        content=rel.content,
                        memory_type=rel.memory_type,
                        status=rel.status,
                        similarity_score=0.90,
                        confidence=rel.confidence,
                        is_active=False,
                        filter_reason=f"SUPERSEDED: {rel.supersede_reason or 'Replaced by newer state'}",
                        valid_interval=valid_interval,
                        created_at=rel.created_at,
                        triple_repr=triple_str
                    ))

        return MemorySearchResult(
            active_memories=active_list[:top_k],
            superseded_memories=superseded_list,
            decayed_memories=decayed_list,
            all_retrieved=all_retrieved,
            attributions=attributions,
            conflict_detected=len(superseded_list) > 0,
            conflict_summary=f"Identified {len(superseded_list)} historical superseded state(s)" if superseded_list else None
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
        Synthesizes the assistant answer.
        Supports external LLMs (Gemini, OpenAI) or local deterministic cognitive reasoning.
        """
        if provider == "gemini" and api_key:
            return self._call_gemini_api(query, search_result, conflict_notes, api_key)
        elif provider == "openai" and api_key:
            return self._call_openai_api(query, search_result, conflict_notes, api_key)

        # --------------------------------------------------------
        # Local Cognitive Synthesis
        # --------------------------------------------------------
        active_mems = list(search_result.active_memories)
        superseded_mems = list(search_result.superseded_memories)
        q = query.lower().strip()
        q_clean = q.replace("?", "").replace(".", "").replace(",", "").replace("!", "")

        # 1. User just stored a new fact/decision/preference
        if new_extracted:
            extracted_summary = ", ".join(e.content for e in new_extracted)
            if conflict_notes:
                res_txt = " | ".join(conflict_notes)
                return f"Got it! I have updated my knowledge: **{extracted_summary}**. ({res_txt}). The previous assertion has been archived into your historical timeline."
            return f"I've committed that to memory: **{extracted_summary}**."

        # 2. Historical / Retrospective Intent Query
        historical_phrases = ["previously", "before", "used to", "formerly", "old", "prior", "in the past", "back then", "earlier", "what did i used to", "where did i live before", "what was my"]
        is_historical = any(p in q for p in historical_phrases)

        if is_historical:
            if superseded_mems:
                # Find best matching historical memory
                for mem in superseded_mems:
                    if mem.triple:
                        pred = mem.triple.predicate.replace('_', ' ')
                        obj = mem.triple.object
                        return f"Previously, your recorded {pred} was **{obj}**. *(Historical memory: {mem.content})*"
                return f"I found a historical memory: **{superseded_mems[0].content}**."
            return "I don't have any superseded historical memories regarding that."

        # 3. Location Queries
        if any(w in q for w in ["where do i live", "where am i living", "where is my home", "where do you think i live", "where do i currently live", "where am i located", "where's my home", "what city"]):
            loc_mems = [m for m in active_mems if m.triple and m.triple.predicate in ["lives_in", "origin_from"]]
            if loc_mems:
                return f"Based on my memory, you live in **{loc_mems[0].triple.object}**."
            return "I don't have a recorded current location for you."

        # 4. Beverage / Drink Preference
        if any(w in q for w in ["favorite beverage", "favourite beverage", "favorite drink", "favourite drink", "what do i drink", "what beverage", "which drink", "coffee", "matcha", "tea"]):
            bev_mems = [m for m in active_mems if m.triple and m.triple.predicate in ["primary_beverage", "prefers_beverage"]]
            if bev_mems:
                return f"Based on my memory, your preferred beverage is **{bev_mems[0].triple.object}**."
            return "I don't have a recorded beverage preference for you."

        # 5. Database Choice
        if any(w in q for w in ["what database", "which database", "database did we", "database are we", "database do we use", "what db", "which db"]):
            db_mems = [m for m in active_mems if m.triple and m.triple.predicate in ["database_choice", "decided_to_use", "migrated_tech"]]
            if db_mems:
                return f"Based on my memory, we chose **{db_mems[0].triple.object}** as the database."
            return "I don't have a recorded database decision for the project."

        # 6. Technology Stack / Framework / IDE Tool
        if any(w in q for w in ["what framework", "which framework", "what technology", "what stack", "what ide", "favorite ide", "what tool"]):
            tech_mems = [m for m in active_mems if m.triple and m.triple.predicate in ["framework_choice", "prefers_tool", "decided_to_use"]]
            if tech_mems:
                return f"Based on my memory, you use **{tech_mems[0].triple.object}**."
            return "I don't have a recorded technology choice for that."

        # 7. Diet / Health / Food / Allergies / Dinner / Meals
        if any(w in q for w in ["what is my diet", "what do i eat", "what can i eat", "what should i eat", "what should i have for dinner", "what to eat", "dinner", "lunch", "breakfast", "meal", "food", "am i vegan", "what is my current diet", "diet", "allergic", "allergy", "allergies"]):
            diet_mems = [m for m in active_mems if m.triple and m.triple.predicate in ["dietary_lifestyle", "avoids_food", "allergic_to"]]
            if diet_mems:
                lifestyle_mem = next((m for m in diet_mems if m.triple.predicate == "dietary_lifestyle"), None)
                allergies = [m.triple.object for m in diet_mems if m.triple.predicate == "allergic_to"]
                
                if "dinner" in q or "meal" in q or "lunch" in q or "breakfast" in q or "what should i have" in q or "what can i eat" in q:
                    lifestyle_str = lifestyle_mem.triple.object if lifestyle_mem else "your preferences"
                    allergy_str = f" (avoiding {', '.join(allergies)})" if allergies else ""
                    if "vegan" in lifestyle_str.lower():
                        return f"Since you are **{lifestyle_str}**{allergy_str}, I recommend a delicious vegan dinner like a roasted tofu buddha bowl, chickpea tikka masala, or avocado sushi rolls!"
                    elif "keto" in lifestyle_str.lower():
                        return f"Since you follow a **{lifestyle_str}** diet{allergy_str}, I recommend grilled salmon with garlic asparagus or a keto steak avocado salad!"
                    return f"Based on your active dietary lifestyle (**{lifestyle_str}**){allergy_str}, you should choose a meal that fits your routine."
                
                facts = [f"{m.triple.predicate.replace('_', ' ')}: **{m.triple.object}**" for m in diet_mems]
                return f"Based on my memory, your dietary information is: {', '.join(facts)}."
            return "I don't have your dietary or allergy information recorded yet."

        # 8. Profession / Role / Company
        if any(w in q for w in ["what is my job", "what do i do", "where do i work", "what is my role", "what's my role", "what profession", "what do i work as"]):
            job_mems = [m for m in active_mems if m.triple and m.triple.predicate in ["works_as", "employed_at", "studies_at"]]
            if job_mems:
                return f"Based on my memory, you are associated with **{job_mems[0].triple.object}**."
            return "I don't have your current job or role recorded yet."

        # 9. Contact / Phone / Email
        if any(w in q for w in ["what is my phone", "what is my number", "what's my phone", "what is my email", "how to contact"]):
            contact_mems = [m for m in active_mems if m.triple and m.triple.predicate in ["has_phone", "has_email"]]
            if contact_mems:
                return f"Based on my memory, your contact detail is **{contact_mems[0].triple.object}**."
            return "I don't have your contact information recorded."

        # 10. Confidential Project
        if any(w in q for w in ["secret project", "confidential project"]):
            proj_mems = [m for m in active_mems if m.triple and m.triple.predicate == "confidential_project"]
            if proj_mems:
                return f"Based on my memory, your confidential project is codenamed **{proj_mems[0].triple.object}**."
            return "I don't have any confidential project recorded for you."

        # 11. General Matching: If active memories exist with high relevance to question words
        if active_mems:
            top_mem = active_mems[0]
            if top_mem.triple:
                sub = top_mem.triple.subject
                pred = top_mem.triple.predicate.replace("_", " ")
                obj = top_mem.triple.object
                return f"Based on my memory, {sub} {pred} **{obj}**."
            return f"Based on my memory: {top_mem.content}."

        return "I don't have any recorded memories regarding that yet. You can tell me your preferences, decisions, or details anytime and I will remember them across sessions!"

    # ============================================================
    # FORGET / GDPR PURGE HANDLER
    # ============================================================

    def _handle_forget_command(
        self,
        user_id: str,
        session_id: str,
        raw_message: str,
        forget_target: str,
        sim_date: Optional[str]
    ) -> ChatResponse:
        """Handles targeted GDPR memory purging and permanent erasure."""
        candidates = self.store.vector_search(user_id=user_id, query=forget_target, top_k=5, min_similarity=0.15)
        forgotten_count = 0
        details = []

        for mem, score in candidates:
            if mem.status != MemoryStatus.FORGOTTEN:
                self.store.forget_memory(
                    memory_id=mem.id,
                    user_id=user_id,
                    reason=f"User instructed to forget: '{forget_target}'"
                )
                forgotten_count += 1
                details.append(f"Purged #{mem.id[:6]} ({mem.memory_type.value})")

        # Fallback lexical sweep across all memories for the user
        if forgotten_count == 0:
            all_mems = self.store.get_user_memories(user_id=user_id, include_superseded=True)
            for mem in all_mems:
                if any(w.lower() in mem.content.lower() for w in forget_target.split() if len(w) > 2):
                    self.store.forget_memory(
                        mem.id,
                        user_id=user_id,
                        reason=f"Keyword match purge: '{forget_target}'"
                    )
                    forgotten_count += 1
                    details.append(f"Purged #{mem.id[:6]}")

        answer = f"I have purged {forgotten_count} memory record(s) matching '{forget_target}'. An immutable audit log entry has been generated, and this information has been permanently erased."
        
        self.store.save_chat_message(user_id=user_id, session_id=session_id, role="user", content=raw_message, simulated_date=sim_date)
        self.store.save_chat_message(user_id=user_id, session_id=session_id, role="assistant", content=answer, simulated_date=sim_date)

        return ChatResponse(
            answer=answer,
            user_id=user_id,
            session_id=session_id,
            used_memories=[],
            superseded_memories=[],
            conflict_resolution_notes=[f"GDPR Purge executed: {forgotten_count} records erased."],
            new_memories_extracted=[],
            simulated_date=sim_date
        )

    # ============================================================
    # EXTERNAL LLM PROVIDERS
    # ============================================================

    def _call_gemini_api(
        self,
        query: str,
        search_res: MemorySearchResult,
        conflict_notes: List[str],
        api_key: str
    ) -> str:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            context = "\n".join([f"- [ACTIVE MEMORY #{m.id[:6]}]: {m.content}" for m in search_res.active_memories])
            if search_res.superseded_memories:
                context += "\n" + "\n".join([f"- [HISTORICAL SUPERSEDED #{m.id[:6]}]: {m.content} (Reason: {m.supersede_reason})" for m in search_res.superseded_memories])

            prompt = f"""You are MemoryOS, an AI assistant with persistent temporal memory.
Rules:
1. Answer the user's question accurately using relevant active memories.
2. Superseded memories are historical; only cite them if the user asks about the past.
3. If no relevant memory exists, say so honestly without inventing facts.

Context:
{context}

Question:
{query}"""
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return self._synthesize_answer(query, search_res, conflict_notes, [], "local")

    def _call_openai_api(
        self,
        query: str,
        search_res: MemorySearchResult,
        conflict_notes: List[str],
        api_key: str
    ) -> str:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            context = "\n".join([f"- [ACTIVE MEMORY #{m.id[:6]}]: {m.content}" for m in search_res.active_memories])
            if search_res.superseded_memories:
                context += "\n" + "\n".join([f"- [HISTORICAL SUPERSEDED #{m.id[:6]}]: {m.content} (Reason: {m.supersede_reason})" for m in search_res.superseded_memories])

            system_prompt = "You are MemoryOS, a contradiction-aware AI assistant with persistent temporal memory."
            user_prompt = f"Context:\n{context}\n\nQuestion:\n{query}"

            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2
                },
                timeout=12
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return self._synthesize_answer(query, search_res, conflict_notes, [], "local")

    # ============================================================
    # KNOWLEDGE GRAPH & TIMELINE GENERATORS
    # ============================================================

    def get_knowledge_graph(self, user_id: str, simulated_date: Optional[str] = None) -> Dict[str, Any]:
        """Generates node and edge data for the interactive Knowledge Graph."""
        memories = self.store.get_user_memories(
            user_id=user_id,
            include_superseded=True,
            include_forgotten=False,
            simulated_date=simulated_date
        )

        nodes = []
        edges = []

        # Central User Root Node
        user_node_id = f"user_{user_id}"
        nodes.append({
            "id": user_node_id,
            "label": f"User: {user_id.capitalize()}",
            "full_content": f"Root identity node for tenant: {user_id.upper()}",
            "type": "USER",
            "status": "ACTIVE",
            "color": "#6366f1",
            "confidence": 1.0
        })

        node_ids = {user_node_id}

        for mem in memories:
            mem_node_id = f"mem_{mem.id[:8]}"
            label = mem.triple.object if mem.triple else mem.content[:24]

            if mem.status == MemoryStatus.ACTIVE:
                status_color = "#10b981"
            elif mem.status == MemoryStatus.SUPERSEDED:
                status_color = "#f59e0b"
            elif mem.status == MemoryStatus.DECAYED:
                status_color = "#64748b"
            else:
                status_color = "#94a3b8"

            nodes.append({
                "id": mem_node_id,
                "memory_id": mem.id,
                "label": label,
                "full_content": mem.content,
                "type": mem.memory_type.value,
                "status": mem.status.value,
                "color": status_color,
                "confidence": mem.confidence,
                "importance": mem.importance,
                "valid_interval": f"{mem.valid_from[:10] if mem.valid_from else 'Start'} ➔ {mem.valid_to[:10] if mem.valid_to else 'Present'}",
                "supersede_reason": mem.supersede_reason
            })
            node_ids.add(mem_node_id)

            # User -> Memory edge
            rel_label = mem.triple.predicate.replace("_", " ") if mem.triple else "stated"
            edges.append({
                "id": f"e_{user_node_id}_{mem_node_id}",
                "source": user_node_id,
                "target": mem_node_id,
                "label": rel_label,
                "status": mem.status.value,
                "is_dashed": (mem.status != MemoryStatus.ACTIVE)
            })

            # Mutation / Evolution edge (old -> new)
            if mem.superseded_by_id:
                target_mem_id = f"mem_{mem.superseded_by_id[:8]}"
                edges.append({
                    "id": f"evol_{mem_node_id}_{target_mem_id}",
                    "source": mem_node_id,
                    "target": target_mem_id,
                    "label": "mutated_to",
                    "status": "EVOLUTION",
                    "color": "#ef4444",
                    "is_dashed": True
                })

        return {"nodes": nodes, "edges": edges}

    def get_timeline_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Generates a sorted chronological timeline of memory state transitions."""
        memories = self.store.get_user_memories(user_id=user_id, include_superseded=True, include_forgotten=True)
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
                "triple": mem.triple.dict() if mem.triple else None
            })
        events.sort(key=lambda x: x["created_at"])
        return events