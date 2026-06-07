# Podcast Q&A Bot — Checkpoint

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Next.js (3000)  │────▶│  FastAPI (8000)   │────▶│  Python Pipeline │
│  - YouTube embed │     │  POST /api/load   │     │  Transcript      │
│  - Chat UI       │     │  POST /api/session│     │  Chunking        │
│  - Timestamp     │     │  POST /api/ask    │     │  Embedding       │
│    auto-play     │     │  In-memory sess   │     │  Reranking       │
└─────────────────┘     └──────────────────┘     │  Groq LLM        │
                                                   └─────────────────┘
```

## Services running

| Service | Port | Command |
|---------|------|---------|
| FastAPI | 8000 | `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` |
| Next.js | 3000 | `cd frontend && npx next dev -p 3000` |

## What works

- ✅ Transcript fetch (youtube-transcript-api, en-IN → en fallback)
- ✅ Token-aware chunking (200 tok chunks, 40 tok overlap)
- ✅ Embedding (all-MiniLM-L6-v2) + ChromaDB indexing
- ✅ Cross-encoder reranker (top-20 → top-5)
- ✅ Groq LLM (Llama 3.1 8B) via LangChain ChatGroq
- ✅ Conversational prompt (feels like "in the discussion")
- ✅ In-memory session history (last 3 exchanges)
- ✅ YouTube embed player with timestamp auto-jump
- ✅ Any YouTube video with captions (error if none exist)

## Key files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI server, 3 endpoints |
| `backend/session.py` | In-memory session manager |
| `backend/schemas.py` | Pydantic request/response models |
| `src/services/qa_pipeline.py` | Retrieval + rerank + LLM pipeline |
| `src/services/vector_store.py` | ChromaDB (per-video collections) |
| `src/services/transcript_service.py` | YouTube transcript fetcher |
| `src/services/chunking_service.py` | Token-aware snippet grouping |
| `src/services/embedding_service.py` | Sentence transformer provider |
| `src/services/reranker.py` | Cross-encoder reranker |
| `src/services/llm_service.py` | Groq via OpenAI SDK (unused, replaced by ChatGroq in pipeline) |
| `src/config.py` | Centralised env-var config |
| `frontend/app/page.js` | Main React page (video + chat) |
| `frontend/app/layout.js` | Root layout (imports globals.css) |
| `frontend/app/globals.css` | Dark-themed styles |
| `.env` | API keys (GROQ_API_KEY required) |

## To start fresh

```powershell
# Terminal 1
cd D:\CuePoint AI
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2 (after models load)
cd D:\CuePoint AI\frontend
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
npx next dev -p 3000
```

## Next likely steps

- [ ] Response streaming (SSE for real-time answer display)
- [ ] Transcript timestamps in the answer text highlighted
- [ ] Suggested follow-up questions
- [ ] Production build (`next build && next start`)
- [ ] Deploy (Railway / Vercel / Docker)
- [ ] Rate limiting, auth
