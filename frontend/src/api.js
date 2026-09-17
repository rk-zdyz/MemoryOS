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
  if (!res.ok) throw new Error(`Chat API error: ${res.statusText}`);
  return await res.json();
}

export async function getMemories(userId = 'riku', includeSuperseded = true, includeForgotten = false, query = '') {
  const params = new URLSearchParams({
    user_id: userId,
    include_superseded: includeSuperseded,
    include_forgotten: includeForgotten
  });
  if (query) params.append('query', query);

  const res = await fetch(`${API_BASE}/memories?${params.toString()}`);
  if (!res.ok) throw new Error(`Get memories error: ${res.statusText}`);
  return await res.json();
}

export async function getKnowledgeGraph(userId = 'riku') {
  const res = await fetch(`${API_BASE}/knowledge-graph?user_id=${userId}`);
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
