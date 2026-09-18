import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ChatView from './components/ChatView';
import MemoryInspector from './components/MemoryInspector';
import KnowledgeGraph from './components/KnowledgeGraph';
import TimelineSlider from './components/TimelineSlider';
import JudgeBenchmarks from './components/JudgeBenchmarks';
import SettingsModal from './components/SettingsModal';
import {
  sendChatMessage,
  getMemories,
  getKnowledgeGraph,
  getTimeline,
  getChatHistory,
  forgetMemory,
  resetDatabase,
  getUsersList
} from './api';

export default function App() {
  const [activeUser, setActiveUser] = useState('riku');
  const [activeTab, setActiveTab] = useState('chat'); // chat, graph, timeline, benchmarks
  const [simulatedDate, setSimulatedDate] = useState(null);
  const [messages, setMessages] = useState([]);
  const [memories, setMemories] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [usersList, setUsersList] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedMemoryId, setHighlightedMemoryId] = useState(null);
  
  // Settings
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [provider, setProvider] = useState('local');
  const [apiKey, setApiKey] = useState('');

  // Load initial data for active user
  useEffect(() => {
    loadUserData(activeUser);
  }, [activeUser]);

  const loadUserData = async (userId) => {
    try {
      const [memsRes, graphRes, timelineRes, histRes, usersRes] = await Promise.all([
        getMemories(userId, true, true),
        getKnowledgeGraph(userId),
        getTimeline(userId),
        getChatHistory(userId),
        getUsersList()
      ]);

      setMemories(memsRes.memories || []);
      setGraphData(graphRes || { nodes: [], edges: [] });
      setTimelineEvents(timelineRes.events || []);
      setUsersList(usersRes.users || []);

      // Format conversation history
      if (histRes.history?.length > 0) {
        setMessages(histRes.history.map(h => ({
          role: h.role,
          content: h.content,
          simulated_date: h.simulated_date,
          created_at: h.created_at,
          used_memories: [],
          superseded_memories: [],
          conflict_notes: []
        })));
      } else {
        setMessages([]);
      }
    } catch (err) {
      console.error("Failed to load user data:", err);
    }
  };

  const handleSendMessage = async (text) => {
  if (isLoading || !text?.trim()) return;

  setIsLoading(true);

  const messageText = text.trim();

  // Immediately add the exact message the user clicked/typed.
  const newMsg = {
    role: 'user',
    content: messageText,
    simulated_date: simulatedDate,
    created_at: new Date().toISOString(),
    used_memories: [],
    superseded_memories: [],
    conflict_notes: []
  };

  setMessages(prev => [...prev, newMsg]);

  try {
    const res = await sendChatMessage(
      activeUser,
      `session_${activeUser}`,
      messageText,
      simulatedDate,
      provider,
      apiKey
    );

    const assistantMsg = {
      role: 'assistant',
      content: res.answer,
      simulated_date: res.simulated_date,
      created_at: new Date().toISOString(),
      used_memories: res.used_memories || [],
      superseded_memories: res.superseded_memories || [],
      conflict_notes: res.conflict_resolution_notes || []
    };

    // Add ONLY the new assistant response.
    // Do NOT reload conversation history here.
    setMessages(prev => [...prev, assistantMsg]);

    // Refresh memory/graph/timeline data WITHOUT touching messages.
    try {
      const [memsRes, graphRes, timelineRes, usersRes] =
        await Promise.all([
          getMemories(activeUser, true, true),
          getKnowledgeGraph(activeUser),
          getTimeline(activeUser),
          getUsersList()
        ]);

      setMemories(memsRes.memories || []);
      setGraphData(graphRes || { nodes: [], edges: [] });
      setTimelineEvents(timelineRes.events || []);
      setUsersList(usersRes.users || []);
    } catch (refreshErr) {
      console.error(
        "Failed to refresh memory data:",
        refreshErr
      );
    }

  } catch (err) {

    setMessages(prev => [
      ...prev,
      {
        role: 'assistant',
        content: `Error communicating with memory engine: ${err.message}`,
        created_at: new Date().toISOString(),
        used_memories: [],
        superseded_memories: [],
        conflict_notes: []
      }
    ]);

  } finally {

    setIsLoading(false);
  }
};

  const handleForgetMemory = async (memoryId) => {
    try {
      await forgetMemory(activeUser, memoryId);
      await loadUserData(activeUser);
    } catch (err) {
      console.error("Failed to forget memory:", err);
    }
  };

  const handleResetDatabase = async () => {
    try {
      await resetDatabase();
      await loadUserData(activeUser);
    } catch (err) {
      console.error("Failed to reset database:", err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-primary)' }}>
      {/* Top Navbar */}
      <Navbar
        activeUser={activeUser}
        onSelectUser={setActiveUser}
        usersList={usersList}
        onReset={handleResetDatabase}
        onOpenSettings={() => setIsSettingsOpen(true)}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        simulatedDay={simulatedDate}
        onSimulatedDayChange={setSimulatedDate}
      />

      {/* Main Workspace Area */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', padding: '12px 16px 16px 16px', gap: '14px' }}>
        {/* Left / Main Workspace Pane */}
        <div className="glass-panel" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {activeTab === 'chat' && (
            <ChatView
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              activeUser={activeUser}
              simulatedDate={simulatedDate}
              onSimulatedDateChange={setSimulatedDate}
              onSelectMemory={(id) => setHighlightedMemoryId(id)}
            />
          )}

          {activeTab === 'graph' && (
            <KnowledgeGraph
              graphData={graphData}
              onRefresh={() => loadUserData(activeUser)}
              onSelectMemory={(id) => setHighlightedMemoryId(id)}
            />
          )}

          {activeTab === 'timeline' && (
            <TimelineSlider
              timelineEvents={timelineEvents}
              activeUser={activeUser}
            />
          )}

          {activeTab === 'benchmarks' && (
            <JudgeBenchmarks
              onBenchmarkComplete={() => loadUserData(activeUser)}
              onSelectUser={setActiveUser}
            />
          )}
        </div>

        {/* Right Cognitive Memory Bank Inspector */}
        <div style={{ width: '380px', height: '100%', overflow: 'hidden', borderRadius: 'var(--radius-md)' }}>
          <MemoryInspector
            memories={memories}
            activeUser={activeUser}
            onForgetMemory={handleForgetMemory}
            onRefresh={() => loadUserData(activeUser)}
            highlightedMemoryId={highlightedMemoryId}
          />
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        provider={provider}
        onProviderChange={setProvider}
        apiKey={apiKey}
        onApiKeyChange={setApiKey}
        onResetDatabase={handleResetDatabase}
      />
    </div>
  );
}
