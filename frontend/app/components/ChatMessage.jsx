'use client';

import { fmtTime, stripChunkLabels } from '../utils/formatAnswer';

export default function ChatMessage({ message, onJumpTo }) {
  const { role, content, sources, _streaming } = message;
  const isUser = role === 'user';

  const cleanContent = isUser ? content : stripChunkLabels(content);
  const isLive = _streaming && !sources?.length;

  const primarySource = sources?.[0];

  return (
    <div className={`chat-msg ${isUser ? 'user' : 'assistant'}`}>
      <div className="msg-avatar">
        {isUser ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 20c0-4 3.5-6 8-6s8 2 8 6" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
          </svg>
        )}
      </div>
      <div className="msg-body">
        <div className="msg-bubble">
          {isLive && !cleanContent ? (
            <div className="streaming-cursor" />
          ) : (
            <>
              <p>{cleanContent}</p>
              {isLive && <span className="streaming-cursor inline" />}
            </>
          )}
          {!isUser && primarySource && (
            <button
              className="jump-btn"
              onClick={() => onJumpTo(primarySource.start)}
            >
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z" />
              </svg>
              Jump to {fmtTime(primarySource.start)}
            </button>
          )}
        </div>
        {!isUser && sources?.length > 1 && (
          <div>
            <hr className="src-divider" />
            <span className="more-sources-label">More timestamps:</span>
            <div className="more-sources">
              {sources.slice(1).map((src, i) => (
                <button key={i} className="src-chip" onClick={() => onJumpTo(src.start)}>
                  {fmtTime(src.start)}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
