# CuePoint AI

Ask questions about YouTube podcasts and jump to the exact timestamp where the answer is discussed.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Next.js (3000)  │────▶│  FastAPI (8000)   │────▶│  Python RAG Pipeline │
│  - YouTube embed │     │  POST /api/load   │     │  Transcript Fetch    │
│  - Chat UI       │     │  POST /api/session│     │  Chunking            │
│  - Timestamp     │     │  POST /api/ask    │     │  Embedding           │
│    auto-play     │     │  POST /api/ask/   │     │  Reranking           │
│  - Streaming     │     │       stream      │     │  Groq LLM            │
│  - Responsive    │     │  POST /api/       │     └─────────────────────┘
│                   │     │       summarize   │
└─────────────────┘     └──────────────────┘
```

## Features

- **Timestamp-accurate answers** — RAG with cross-encoder reranking pinpoints the exact moment in the video
- **Streaming responses** — tokens appear in real-time as the LLM generates
- **Video summarization** — map-reduce summarization of entire transcripts
- **Responsive design** — olive green / beige academic theme, works on desktop and mobile
- **YouTube integration** — load any video with captions and jump to timestamps

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Groq API key](https://console.groq.com)

### Backend

```bash
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Groq API key:

```env
GROQ_API_KEY=gsk_your_key_here
```

### Frontend

```bash
cd frontend
npm install
```

### Run

Terminal 1 — Backend:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 — Frontend:

```bash
cd frontend
npm run dev
```

Open **http://localhost:3000**

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/load` | Fetch transcript, chunk, and index a YouTube video |
| POST | `/api/session` | Create a new chat session |
| POST | `/api/ask` | Ask a question (non-streaming) |
| POST | `/api/ask/stream` | Ask a question (SSE streaming) |
| POST | `/api/summarize` | Generate a full video summary |

## Stack

- **Backend**: FastAPI, LangChain, Groq (Llama 3.1 8B), ChromaDB, sentence-transformers, cross-encoder reranker
- **Frontend**: Next.js 16, React 19, react-youtube
- **Theme**: Olive green / beige academic palette, Source Serif 4 + Hanken Grotesk
