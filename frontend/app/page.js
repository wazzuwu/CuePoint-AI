'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import VideoPanel from './components/VideoPanel';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import EmptyState from './components/EmptyState';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [videoId, setVideoId] = useState('Rni7Fz7208c');
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [streamingId, setStreamingId] = useState(null);
  const [error, setError] = useState('');
  const [player, setPlayer] = useState(null);
  const chatEnd = useRef(null);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    loadVideo('Rni7Fz7208c');
  }, []);

  const loadVideo = useCallback(async (urlOrId) => {
    if (!urlOrId) return;
    setBusy(true);
    setError('');
    try {
      const r = await fetch(`${API_BASE}/api/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: urlOrId }),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || 'Failed to load video');
      }
      const data = await r.json();
      setVideoId(data.video_id);

      const s = await fetch(`${API_BASE}/api/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: data.video_id }),
      });
      if (!s.ok) throw new Error('Failed to create session');
      const sdata = await s.json();
      setSessionId(sdata.session_id);
      setMessages([]);
    } catch (e) {
      setError(e.message);
      setVideoId('');
    } finally {
      setBusy(false);
    }
  }, []);



  const askQuestion = async (question) => {
    if (!question.trim() || !sessionId) return;

    const msgId = Date.now().toString();
    setMessages(prev => [
      ...prev,
      { role: 'user', content: question, _id: msgId + '_user' },
      { role: 'assistant', content: '', sources: [], _id: msgId, _streaming: true },
    ]);
    setStreamingId(msgId);
    setBusy(true);

    try {
      const r = await fetch(`${API_BASE}/api/ask/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, question }),
      });
      if (!r.ok) throw new Error('Failed to get answer');

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') continue;
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'sources') {
              setMessages(prev => prev.map(m =>
                m._id === msgId
                  ? { ...m, sources: parsed.sources, _streaming: false }
                  : m
              ));
            } else if (parsed.token) {
              fullText += parsed.token;
              setMessages(prev => prev.map(m =>
                m._id === msgId
                  ? { ...m, content: fullText }
                  : m
              ));
            }
          } catch { /* skip malformed JSON */ }
        }
      }
    } catch (e) {
      setMessages(prev => prev.map(m =>
        m._id === msgId
          ? { ...m, content: 'Sorry, something went wrong.', _streaming: false }
          : m
      ));
    } finally {
      setStreamingId(null);
      setBusy(false);
    }
  };

  const generateSummary = async () => {
    if (!videoId) return;
    setSummarizing(true);
    try {
      const r = await fetch(`${API_BASE}/api/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: videoId }),
      });
      if (!r.ok) throw new Error('Failed to generate summary');
      const data = await r.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, sources: data.sources }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, failed to generate summary.' }]);
    } finally {
      setSummarizing(false);
    }
  };

  const jumpTo = (seconds) => {
    if (player) {
      player.seekTo(seconds);
      player.playVideo();
    }
  };

  return (
    <div className="app">
      <VideoPanel
        videoId={videoId}
        onLoadVideo={loadVideo}
        onSummarize={generateSummary}
        busy={busy}
        summarizing={summarizing}
        error={error}
        onReady={setPlayer}
      />

      <div className="chat-panel">
        <div className="chat-header">
          <svg className="chat-header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
          </svg>
          <div className="chat-header-text">
            <h2>Analyze Transcript</h2>
            <p>Ask anything about this video</p>
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && !busy && <EmptyState error={error} />}
          {messages.map((msg, i) => (
            <ChatMessage key={msg._id || i} message={msg} onJumpTo={jumpTo} />
          ))}
          {busy && !streamingId && (
            <div className="chat-msg assistant">
              <div className="msg-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                </svg>
              </div>
              <div className="msg-body">
                <div className="msg-bubble typing">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={chatEnd} />
        </div>

        <ChatInput onSend={askQuestion} disabled={!sessionId} busy={busy} />
      </div>
    </div>
  );
}
