const API_BASE = '/api';

export async function sendChatMessage(userId, sessionId, message, simulatedDate = null, provider = 'local', apiKey = null) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      session_id: sessionId,
      message,
      simulated_date: simulatedDate,
      provider,
      api_key: apiKey
    })
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Chat error (${res.status}): ${errorText}`);
  }
  return await res.json();
}

export async function getMemories(userId = 'riku', includeSuperseded = true, includeForgotten = false, query = '', simulatedDate = null) {
  const params = new URLSearchParams({
    user_id: userId,
    include_superseded: includeSuperseded,
    include_forgotten: includeForgotten
  });
  if (query) params.append('query', query);
  if (simulatedDate) params.append('simulated_date', simulatedDate);

  const res = await fetch(`${API_BASE}/memories?${params.toString()}`);
  if (!res.ok) throw new Error(`Get memories error: ${res.statusText}`);
  return await res.json();
}

export async function createManualMemory(userId, content, memoryType = 'PROFILE_FACT', predicate = null, object = null, importance = 0.8, simulatedDate = null) {
  const res = await fetch(`${API_BASE}/memories/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      content,
      memory_type: memoryType,
      predicate,
      object,
      importance,
      simulated_date: simulatedDate
    })
  });
  if (!res.ok) throw new Error(`Create memory error: ${res.statusText}`);
  return await res.json();
}

export async function deleteMemory(userId, memoryId) {
  const res = await fetch(`${API_BASE}/memories/${encodeURIComponent(memoryId)}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Delete memory error: ${res.statusText}`);
  return await res.json();
}

export async function getKnowledgeGraph(userId = 'riku', simulatedDate = null) {
  const params = new URLSearchParams({ user_id: userId });
  if (simulatedDate) params.append('simulated_date', simulatedDate);
  const res = await fetch(`${API_BASE}/knowledge-graph?${params.toString()}`);
  if (!res.ok) throw new Error(`Knowledge graph error: ${res.statusText}`);
  return await res.json();
}

export async function getTimeline(userId = 'riku') {
  const res = await fetch(`${API_BASE}/timeline?user_id=${userId}`);
  if (!res.ok) throw new Error(`Timeline error: ${res.statusText}`);
  return await res.json();
}

export async function getChatHistory(userId = 'riku', sessionId = null) {
  const params = new URLSearchParams({ user_id: userId });
  if (sessionId) params.append('session_id', sessionId);
  
  const res = await fetch(`${API_BASE}/history?${params.toString()}`);
  if (!res.ok) throw new Error(`History error: ${res.statusText}`);
  return await res.json();
}

export async function forgetMemory(userId, target, reason = 'User requested deletion') {
  const res = await fetch(`${API_BASE}/forget`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, target, reason })
  });
  if (!res.ok) throw new Error(`Forget error: ${res.statusText}`);
  return await res.json();
}

export async function resetDatabase(userId = null) {
  const res = await fetch(`${API_BASE}/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId })
  });
  if (!res.ok) throw new Error(`Reset error: ${res.statusText}`);
  return await res.json();
}

export async function getUsersList() {
  const res = await fetch(`${API_BASE}/users`);
  if (!res.ok) throw new Error(`Users list error: ${res.statusText}`);
  return await res.json();
}

export async function getSystemStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(`Stats error: ${res.statusText}`);
  return await res.json();
}

export async function getAuditLogs(userId = null) {
  const params = userId ? `?user_id=${userId}` : '';
  const res = await fetch(`${API_BASE}/audit-logs${params}`);
  if (!res.ok) throw new Error(`Audit logs error: ${res.statusText}`);
  return await res.json();
}
