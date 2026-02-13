from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    context: str | None = None
    button_prompt: str | None = None


class ChatEvent(BaseModel):
    type: str
    content: str | None = None
    filename: str | None = None


class RagSearchRequest(BaseModel):
    query: str
    limit: int = 10
    collection: str | None = None


class RagSearchResult(BaseModel):
    title: str
    authors: str
    year: int | None = None
    relevance: float | None = None
    snippet: str | None = None


class RagSearchResponse(BaseModel):
    results: list[RagSearchResult] = []


class Button(BaseModel):
    id: str
    name: str
    prompt: str
    icon: str | None = None


class ButtonsResponse(BaseModel):
    buttons: list[Button]


class ButtonCreateRequest(BaseModel):
    id: str | None = None
    name: str
    prompt: str
    icon: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    time: str
