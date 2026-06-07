"""Pydantic request/response schemas for the FastAPI backend."""
from pydantic import BaseModel


class LoadRequest(BaseModel):
    video_id: str


class LoadResponse(BaseModel):
    video_id: str
    title: str = ""
    chunks: int = 0
    status: str = "ok"


class AskRequest(BaseModel):
    session_id: str
    question: str


class Source(BaseModel):
    chunk_id: str
    text: str
    start: float
    end: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
