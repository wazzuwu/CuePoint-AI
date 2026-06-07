"""FastAPI backend for the Podcast Q&A Bot."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from backend.schemas import AskRequest, AskResponse, LoadRequest, LoadResponse, Source
from backend.session import create_session, get_session
from src.services.chunking_service import chunk_transcript
from src.services.transcript_service import create_transcript_provider

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("backend")


def _extract_video_id(value: str) -> str:
    """Extract YouTube video ID from a URL or return the value as-is."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, value)
        if m:
            return m.group(1)
    raise HTTPException(status_code=400, detail=f"Invalid YouTube URL or video ID: {value}")


_indexed: set[str] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Backend starting")
    yield
    log.info("Backend shutting down")


app = FastAPI(title="Podcast Q&A Bot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/load")
async def load_video(req: LoadRequest) -> LoadResponse:
    """Fetch transcript, chunk, and index a YouTube video."""
    video_id = _extract_video_id(req.video_id)

    if video_id in _indexed:
        return LoadResponse(video_id=video_id, status="already_indexed")

    provider = create_transcript_provider()
    try:
        transcript = provider.fetch(video_id)
    except Exception as exc:
        err_name = type(exc).__name__
        log.warning("Failed to fetch transcript for %s: %s: %s", video_id, err_name, exc)
        raise HTTPException(
            status_code=404,
            detail=f"No transcript available for this video ({err_name}). "
            f"The video may have no captions or may not exist.",
        )

    chunks = chunk_transcript(transcript)

    from src.services.embedding_service import get_embedding_provider
    from src.services.vector_store import VectorStore

    ep = get_embedding_provider()
    store = VectorStore(collection_name=f"podcast_{video_id}")
    store.add_chunks(chunks)

    _indexed.add(video_id)

    log.info("Indexed %s: %d chunks", video_id, len(chunks))
    return LoadResponse(
        video_id=video_id,
        title=f"YouTube video {video_id}",
        chunks=len(chunks),
        status="ok",
    )


@app.post("/api/ask/stream")
async def ask_question_stream(req: AskRequest) -> StreamingResponse:
    """Stream answer tokens via SSE."""
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    history = session.messages or None

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def producer():
            try:
                for token in session.pipeline.ask_stream(req.question, history=history):
                    loop.call_soon_threadsafe(queue.put_nowait, token)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, producer)

        full_answer = []
        while True:
            token = await queue.get()
            if token is None:
                break
            full_answer.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        full_text = "".join(full_answer)
        session.add_exchange(req.question, full_text)

        sources = [
            Source(
                chunk_id=s["id"],
                text=s["text"],
                start=s["metadata"]["start"],
                end=s["metadata"]["end"],
            )
            for s in getattr(session.pipeline, '_last_sources', [])
        ]
        if sources:
            yield f"data: {json.dumps({'type': 'sources', 'sources': [s.model_dump() for s in sources]})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/ask")
async def ask_question(req: AskRequest) -> AskResponse:
    """Answer a question in a session (non-streaming fallback)."""
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    history = session.messages or None
    result = session.pipeline.ask(req.question, history=history)

    session.add_exchange(req.question, result["answer"])

    sources = [
        Source(
            chunk_id=s["id"],
            text=s["text"],
            start=s["metadata"]["start"],
            end=s["metadata"]["end"],
        )
        for s in result["sources"]
    ]

    return AskResponse(answer=result["answer"], sources=sources)


@app.post("/api/summarize")
async def summarize_video(req: LoadRequest) -> AskResponse:
    """Generate a comprehensive summary of the loaded video."""
    video_id = _extract_video_id(req.video_id)

    if video_id not in _indexed:
        raise HTTPException(
            status_code=400,
            detail=f"Video {video_id} not loaded yet. POST /api/load first.",
        )

    from src.services.qa_pipeline import QAPipeline

    pipeline = QAPipeline(video_id=video_id)
    result = pipeline.summarize()

    sources = [
        Source(
            chunk_id=s["id"],
            text=s["text"],
            start=s["metadata"]["start"],
            end=s["metadata"]["end"],
        )
        for s in result["sources"]
    ]

    return AskResponse(answer=result["answer"], sources=sources)


@app.post("/api/session")
async def new_session(req: LoadRequest) -> dict:
    """Create a new chat session for a video."""
    video_id = _extract_video_id(req.video_id)

    if video_id not in _indexed:
        raise HTTPException(
            status_code=400,
            detail=f"Video {video_id} not loaded yet. POST /api/load first.",
        )

    sid = create_session(video_id)
    return {"session_id": sid, "video_id": video_id}
