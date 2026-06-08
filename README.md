# CuePoint AI

Ask questions about YouTube podcasts and jump to the exact timestamp where the answer is discussed. Designed for local deployment — no cloud services required beyond Groq for the LLM.

> **Screenshot placeholder**
>
> *Replace this with a screenshot of the app showing a question and answer with timestamp links.*
>
> ![App screenshot]()

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌──────────────────────────┐
│   Next.js 16 (3000)  │────▶│   FastAPI (8000)    │────▶│   Python RAG Pipeline    │
│  ─────────────────── │     │  ────────────────── │     │  ─────────────────────── │
│  • YouTube embed     │     │  POST /api/load     │     │  • YouTube Transcript   │
│  • Chat UI           │     │  POST /api/session  │     │  • Token-aware chunking │
│  • Timestamp jump    │     │  POST /api/ask      │     │  • ChromaDB + ONNX       │
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

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
```

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

Open **[http://localhost:3000](http://localhost:3000)** in your browser. The default video (Lex Fridman / Elon Musk) will load automatically.

> **Screenshot placeholder**
>
> *Replace this with a screenshot of the running app with the default video loaded and the chat interface ready.*
>
> ![Chat interface]()

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

## Configuration

All settings are via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key (required) |
| `TRANSCRIPT_LANGUAGES` | `en-IN,en` | YouTube caption language preference |
| `CHUNK_TARGET_TOKENS` | `200` | Target tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | `40` | Overlap tokens between chunks |
| `RETRIEVAL_TOP_K` | `7` | Number of chunks to retrieve for context |
| `LLM_MODEL` | `llama-3.1-8b-instant` | Groq LLM model ID |
| `LLM_TEMPERATURE` | `0.3` | LLM temperature |
| `LLM_MAX_TOKENS` | `512` | Max tokens per LLM response |

## Screenshots

> **Desktop view**
>
> *Replace this with a screenshot of the full desktop layout — video player on the left, chat on the right.*
>
> ![Desktop view]()

> **Mobile view**
>
> *Replace this with a screenshot of the mobile layout — compact mini-player, inline inputs.*
>
> ![Mobile view]()

> **Timestamp jump**
>
> *Replace this with a screenshot showing a clicked timestamp jumping to that point in the video.*
>
> ![Timestamp jump]()

## Stack

| Layer | Technology |
|-------|-----------|
| **Backend framework** | FastAPI, Uvicorn |
| **LLM provider** | Groq (Llama 3.1) via LangChain |
| **Vector store** | ChromaDB (persistent) |
| **Embeddings** | ChromaDB ONNX default (no PyTorch needed) |
| **Frontend** | Next.js 16, React 19 |
| **Video player** | react-youtube |
| **Streaming** | Server-Sent Events (SSE) |
