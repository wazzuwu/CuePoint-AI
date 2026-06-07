'use client';

import { useState } from 'react';
import YouTube from 'react-youtube';

export default function VideoPanel({ videoId, onLoadVideo, onSummarize, busy, summarizing, error, onReady }) {
  const [inputUrl, setInputUrl] = useState('');

  const opts = {
    height: '100%',
    width: '100%',
    playerVars: { rel: 0, modestbranding: 1 },
  };

  return (
    <aside className="video-panel">
      <div className="panel-header">
        <h1>CuePoint AI</h1>
        <div className="panel-status">
          <span className="status-dot" />
          <span className="status-label">{videoId ? 'Ready' : 'Idle'}</span>
        </div>
      </div>

      <div className="panel-scroll">
        <div className="player-wrap">
          <YouTube videoId={videoId} opts={opts} onReady={(e) => onReady(e.target)} />
        </div>

        <div className="video-controls">
          <div className="input-group">
            <input
              placeholder="YouTube URL or video ID"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onLoadVideo(inputUrl.trim())}
            />
            <button onClick={() => onLoadVideo(inputUrl.trim())} disabled={busy}>
              {busy ? 'Loading...' : 'Load'}
            </button>
          </div>
          {error && <div className="video-error">{error}</div>}
        </div>

        <button
          className="summary-btn"
          onClick={onSummarize}
          disabled={!videoId || summarizing}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {summarizing ? 'Generating Summary...' : 'Generate Video Summary'}
        </button>

        <div className="panel-footer">
          <a href="https://github.com/wazzuwu" target="_blank" rel="noopener noreferrer">
            Github.com/wazzuwu
          </a>
        </div>
      </div>
    </aside>
  );
}
