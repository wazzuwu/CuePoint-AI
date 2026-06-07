"""In-memory session manager with simple sliding-window conversation history.

Each session stores:
  - video_id  : str
  - messages  : list[BaseMessage]  (last 6 messages = 3 exchanges)
  - pipeline  : QAPipeline (lazy, created per video)
"""

from __future__ import annotations

import uuid
from typing import Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.services.qa_pipeline import QAPipeline

MAX_EXCHANGES = 3  # keep last 3 question/answer pairs


class Session:
    __slots__ = ("video_id", "messages", "pipeline")

    def __init__(self, video_id: str) -> None:
        self.video_id = video_id
        self.messages: List[BaseMessage] = []
        self.pipeline = QAPipeline(video_id=video_id)

    def add_exchange(self, question: str, answer: str) -> None:
        self.messages.append(HumanMessage(content=question))
        self.messages.append(AIMessage(content=answer))
        # Trim to MAX_EXCHANGES * 2
        if len(self.messages) > MAX_EXCHANGES * 2:
            self.messages = self.messages[-(MAX_EXCHANGES * 2):]


_sessions: Dict[str, Session] = {}


def create_session(video_id: str) -> str:
    """Create a new session and return its ID."""
    sid = uuid.uuid4().hex[:12]
    _sessions[sid] = Session(video_id)
    return sid


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
