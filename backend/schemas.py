"""Skema request/response API (PRD §20)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    environment: str
    database: bool
    vector_extension: bool
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    embedding_dim: int


class SourceItem(BaseModel):
    """Asal potongan dokumen yang dipakai menyusun jawaban (PRD §20)."""

    filename: str
    score: float
    chunk_index: int | None = None
    excerpt: str


class UploadResponse(BaseModel):
    filename: str
    status: Literal["processed", "stored"]
    chunks: int = 0
    detail: str | None = None


class TextDocumentRequest(BaseModel):
    """Menambahkan dokumen dari teks langsung, tanpa unggah berkas."""

    filename: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class DocumentSummary(BaseModel):
    filename: str
    chunks: int
    created_at: datetime


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class QueryResponse(BaseModel):
    """Hasil retrieval mentah, tanpa melibatkan LLM.

    Dipakai untuk menguji mutu pencarian secara terpisah dari mutu jawaban.
    """

    query: str
    results: list[SourceItem]


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str
    tool_used: str
    sources: list[SourceItem] = Field(default_factory=list)


class ChatMessageItem(BaseModel):
    id: int
    session_id: str
    role: str
    message: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageItem]


class ErrorResponse(BaseModel):
    detail: str
    context: dict[str, Any] | None = None
