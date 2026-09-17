import os
import json
import requests
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from backend.memory.models import (
    MemoryEntry, MemoryStatus, MemoryType, MemoryAttribution,
    MemorySearchResult, ChatRequest, ChatResponse
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

    def process_chat(self, req: ChatRequest) -> ChatResponse:
        user_id = req.user_id
        session_id = req.session_id
        message = req.message
        sim_date = req.simulated_date

        # 1. Check for explicit forget / delete / purge commands
        forget_target = self.extractor.detect_forget_request(message)
        if forget_target:
            return self._handle_forget_command(user_id, session_id, message, forget_target, sim_date)

        # 2. Extract new memories & facts from message
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
            # Detect and resolve any contradictions with previous active memories
            resolutions = self.resolver.resolve_conflicts_for_new_memory(mem, simulated_date=sim_date)
            for res in resolutions:
                if res.get("reason"):
                    conflict_notes.append(res["reason"])

        # 3. Run decay & temporal expiration pass
        self.decay_manager.run_lifecycle_pass(user_id, simulated_current_date=sim_date)

        # 4. Retrieve memories for question answering & attribution
        search_res = self.retrieve_with_attribution(user_id=user_id, query=message, top_k=6)

        # Touch accessed active memories to reinforce retention
        for mem in search_res.active_memories:
            self.store.touch_memory(mem.id)

        # 5. Synthesize answer with explainability & conflict awareness
        answer = self._synthesize_answer(
            query=message,
            search_result=search_res,
            conflict_notes=conflict_notes,
            new_extracted=new_extracted,
            provider=req.provider,
            api_key=req.api_key
        )

        # 6. Save message to persistent SQLite conversation history
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

        active_attributions = [a for a in search_res.attributions if a.is_active]
        superseded_attributions = [a for a in search_res.attributions if not a.is_active]

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

    def retrieve_with_attribution(self, user_id: str, query: str, top_k: int = 6) -> MemorySearchResult:
        """
        Retrieves candidate memories via semantic vector search, separates active from
        superseded/decayed, and compiles clear attribution metadata explaining why
        each memory is included or filtered.
        """
        scored_candidates = self.store.vector_search(user_id=user_id, query=query, top_k=top_k * 2, min_similarity=0.15)
        
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
                valid_interval += f" -> To: {mem.valid_to[:10]}"
            else:
                valid_interval += " -> Present"

            triple_str = f"({mem.triple.subject} -> {mem.triple.predicate} -> {mem.triple.object})" if mem.triple else None

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
                    filter_reason=f"SUPERSEDED: {mem.supersede_reason or 'Replaced by newer update'}",
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
                    filter_reason="DECAYED: Relevance decayed over time due to inactivity",
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
                    filter_reason="EXPIRED: Time-bound schedule/event has passed",
                    valid_interval=valid_interval,
                    created_at=mem.created_at,
                    triple_repr=triple_str
                ))
        # Also include historical predecessor memories superseded by retrieved active memories
        for act_mem in list(active_list):
            if act_mem.triple:
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
                            valid_interval += f" -> To: {rel.valid_to[:10]}"
                        else:
                            valid_interval += " -> Present"
                        triple_str = f"({rel.triple.subject} -> {rel.triple.predicate} -> {rel.triple.object})" if rel.triple else None
                        attributions.append(MemoryAttribution(
                            memory_id=rel.id,
                            content=rel.content,
                            memory_type=rel.memory_type,
                            status=rel.status,
                            similarity_score=0.95,
                            confidence=rel.confidence,
                            is_active=False,
                            filter_reason=f"SUPERSEDED: {rel.supersede_reason or 'Replaced by newer update'}",
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
            conflict_summary=f"Identified {len(superseded_list)} superseded historical record(s)" if superseded_list else None
        )

    def _handle_forget_command(self, user_id: str, session_id: str, raw_message: str, forget_target: str, sim_date: Optional[str]) -> ChatResponse:
        """Executes targeted GDPR-style selective memory erasure"""
        candidates = self.store.vector_search(user_id=user_id, query=forget_target, top_k=5, min_similarity=0.2)
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
                details.append(f"Purged memory ID #{mem.id[:8]} ({mem.memory_type.value})")

        if forgotten_count == 0:
            # Check all user memories for direct keyword match
            all_mems = self.store.get_user_memories(user_id=user_id, include_superseded=True)
            for mem in all_mems:
                if any(w.lower() in mem.content.lower() for w in forget_target.split() if len(w) > 2):
                    self.store.forget_memory(mem.id, user_id=user_id, reason=f"Keyword match purge: '{forget_target}'")
                    forgotten_count += 1
                    details.append(f"Purged memory ID #{mem.id[:8]}")

        answer = f"I have purged {forgotten_count} memory record(s) matching '{forget_target}'. An immutable audit log entry has been generated, and this information will never be recalled."
        
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
        Synthesizes an intelligent, contradiction-aware response.
        If an external API key (Gemini / OpenAI) is provided, connects to it.
        Otherwise, uses the built-in deterministic cognitive synthesis engine.
        """
        # If external provider requested with API key
        if provider == "gemini" and api_key:
            return self._call_gemini_api(query, search_result, conflict_notes, api_key)
        elif provider == "openai" and api_key:
            return self._call_openai_api(query, search_result, conflict_notes, api_key)

        # Built-in Cognitive Synthesis Engine (Works offline 100% reliably)
        active_mems = search_result.active_memories
        superseded_mems = search_result.superseded_memories

        q_lower = query.lower()

        # If user just updated a fact / told something new
        if new_extracted:
            extracted_summary = ", ".join([e.content for e in new_extracted])
            if conflict_notes:
                resolution_txt = " | ".join(conflict_notes)
                return f"Got it! I've updated my knowledge: **{extracted_summary}**. ({resolution_txt}). I have archived the previous state into your historical timeline."
            return f"I've committed that to memory: **{extracted_summary}**."

        # If user is asking a question
        if active_mems:
            top_active = active_mems[0]
            
            # Formulate clear response
            main_fact = top_active.content
            if top_active.triple:
                sub = top_active.triple.subject
                pred = top_active.triple.predicate.replace('_', ' ')
                obj = top_active.triple.object
                qual = f" ({top_active.triple.qualifier})" if top_active.triple.qualifier else ""
                main_fact = f"{sub} {pred} **{obj}**{qual}"

            response_parts = [f"Based on my memory, {main_fact}."]

            # If other relevant active memories exist
            if len(active_mems) > 1:
                extras = [m.content for m in active_mems[1:3]]
                response_parts.append(f"I also recall: {'; '.join(extras)}.")

            # If there's an outdated superseded fact that directly relates to this topic, explain the lineage!
            if superseded_mems:
                top_super = superseded_mems[0]
                if top_super.supersede_reason:
                    response_parts.append(f"*(Note: Historical record shows '{top_super.content}', but this was superseded: {top_super.supersede_reason})*")

            return " ".join(response_parts)

        # If no active memory found
        if superseded_mems:
            top_super = superseded_mems[0]
            return f"I found a historical memory that you previously stated '{top_super.content}', but that information is marked as SUPERSEDED ({top_super.supersede_reason or 'outdated'}) and no longer active."

        return f"I don't have any recorded memories regarding that yet. You can tell me your preferences, decisions, or details anytime and I will remember them across sessions!"

    def _call_gemini_api(self, query: str, search_res: MemorySearchResult, conflict_notes: List[str], api_key: str) -> str:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            context = "\n".join([f"- [ACTIVE MEMORY #{m.id[:6]}]: {m.content}" for m in search_res.active_memories])
            if search_res.superseded_memories:
                context += "\n" + "\n".join([f"- [HISTORICAL SUPERSEDED #{m.id[:6]} - DO NOT USE AS CURRENT TRUTH]: {m.content} (Reason: {m.supersede_reason})" for m in search_res.superseded_memories])

            prompt = f"System: You are ChronosMemory, an AI assistant with strict temporal awareness. Answer the user using ONLY the active memories. If a historical memory was superseded, you may acknowledge the change.\nActive Memory Context:\n{context}\n\nUser Question: {query}"
            
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return self._synthesize_answer(query, search_res, conflict_notes, [], "local")

    def _call_openai_api(self, query: str, search_res: MemorySearchResult, conflict_notes: List[str], api_key: str) -> str:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            context = "\n".join([f"- [ACTIVE MEMORY #{m.id[:6]}]: {m.content}" for m in search_res.active_memories])
            if search_res.superseded_memories:
                context += "\n" + "\n".join([f"- [HISTORICAL SUPERSEDED #{m.id[:6]}]: {m.content} (Reason: {m.supersede_reason})" for m in search_res.superseded_memories])

            messages = [
                {"role": "system", "content": f"You are ChronosMemory with temporal memory. Rely strictly on active memories.\n{context}"},
                {"role": "user", "content": query}
            ]
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, json={"model": "gpt-4o-mini", "messages": messages}, timeout=10)
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return self._synthesize_answer(query, search_res, conflict_notes, [], "local")

    def get_knowledge_graph(self, user_id: str) -> Dict[str, Any]:
        """Generates node & edge data for Knowledge Graph visualization"""
        memories = self.store.get_user_memories(user_id=user_id, include_superseded=True, include_forgotten=False)
        nodes = []
        edges = []
        
        # Central User Node
        user_node_id = f"user_{user_id}"
        nodes.append({
            "id": user_node_id,
            "label": f"User: {user_id.capitalize()}",
            "type": "USER",
            "status": "ACTIVE",
            "color": "#6366f1"
        })

        node_ids = {user_node_id}

        for mem in memories:
            mem_node_id = f"mem_{mem.id[:8]}"
            label = mem.triple.object if mem.triple else mem.content[:24]
            status_color = "#10b981" if mem.status == MemoryStatus.ACTIVE else ("#f59e0b" if mem.status == MemoryStatus.SUPERSEDED else "#6b7280")
            
            nodes.append({
                "id": mem_node_id,
                "label": label,
                "full_content": mem.content,
                "type": mem.memory_type.value,
                "status": mem.status.value,
                "color": status_color,
                "confidence": mem.confidence,
                "valid_interval": f"{mem.valid_from[:10] if mem.valid_from else ''} -> {mem.valid_to[:10] if mem.valid_to else 'Now'}",
                "supersede_reason": mem.supersede_reason
            })
            node_ids.add(mem_node_id)

            # Edge from User to Memory
            rel_label = mem.triple.predicate.replace('_', ' ') if mem.triple else "stated"
            edges.append({
                "id": f"e_{user_node_id}_{mem_node_id}",
                "source": user_node_id,
                "target": mem_node_id,
                "label": rel_label,
                "status": mem.status.value,
                "is_dashed": mem.status != MemoryStatus.ACTIVE
            })

            # If superseded by another memory, draw evolution link
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
        """Generates sorted chronological timeline of memory state transitions"""
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
