# CuePoint AI

Ask questions about YouTube podcasts and jump to the exact timestamp where the answer is discussed.

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌──────────────────────────┐
│   Next.js 16 (3000)  │────▶│   FastAPI (8000)    │────▶│   Python RAG Pipeline    │
│  ─────────────────── │     │  ────────────────── │     │  ─────────────────────── │
│  • YouTube embed     │     │  POST /api/load     │     │  • YouTube Transcript   │
│  • Chat UI           │     │  POST /api/session  │     │  • Token-aware chunking │
│  • Timestamp jump    │     │  POST /api/ask      │     │  • Sentence Embeddings   │
│  • SSE streaming     │     │  POST /api/ask/     │     │  • Similarity Search     │
│  • Dark academic     │     │       stream        │     │  • Groq LLM (Llama 3.1) │
│    theme             │     │  POST /api/         │     └──────────────────────────┘
│                      │     │       summarize     │
└─────────────────────┘     └─────────────────────┘
```

## Features

- **Timestamp-accurate answers** — RAG pipeline retrieves relevant transcript segments and provides clickable timestamps that jump directly to the discussed moment in the YouTube player
- **Real-time streaming** — SSE-based token streaming renders answers incrementally as the LLM generates them
- **Full video summarization** — map-reduce summarization condenses entire transcripts into a coherent overview
- **Multi-video sessions** — load any YouTube video with captions, create chat sessions, and maintain conversational context across exchanges
- **Responsive dark academic theme** — olive green / beige palette with serif typography, optimized for desktop and mobile

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Groq API key](https://console.groq.com)

### 1. Backend Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure your Groq API key:

```env
GROQ_API_KEY=gsk_your_key_here
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

### 3. Run Locally

Terminal 1 — Backend:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 — Frontend:

```bash
cd frontend
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/load` | Fetch transcript, chunk, and index a YouTube video |
| POST | `/api/session` | Create a new chat session for an indexed video |
| POST | `/api/ask` | Ask a question (non-streaming response) |
| POST | `/api/ask/stream` | Ask a question (SSE streaming response) |
| POST | `/api/summarize` | Generate a full video summary |

### Example: Load a video

```bash
curl -X POST http://localhost:8000/api/load \
  -H "Content-Type: application/json" \
  -d '{"video_id": "https://youtube.com/watch?v=Rni7Fz7208c"}'
```

### Example: Ask a question (streaming)

```bash
curl -X POST http://localhost:8000/api/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session_id>", "question": "What was said about AI safety?"}'
```

## Deployment

### Render (Free Tier)

The project includes a `vercel.json` for the frontend and is configured to run on Render for the backend. The backend uses `sentence-transformers` with `all-MiniLM-L6-v2` for embeddings and ChromaDB for vector storage.

Key environment variables for deployment:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key (required) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CHROMA_PERSIST_DIR` | `data/chroma` | Vector store persistence path |
| `RETRIEVAL_TOP_K` | `7` | Number of chunks to retrieve |
| `LLM_MODEL` | `llama-3.1-8b-instant` | Groq LLM model ID |

## Stack

| Layer | Technology |
|-------|-----------|
| **Backend framework** | FastAPI, Uvicorn |
| **LLM provider** | Groq (Llama 3.1 8B) via LangChain |
| **Vector store** | ChromaDB (persistent) |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **Frontend** | Next.js 16, React 19 |
| **Video player** | react-youtube |
| **Streaming** | Server-Sent Events (SSE) |
