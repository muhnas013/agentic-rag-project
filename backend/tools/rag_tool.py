"""Tool 1 — RAG Search (PRD §8).

Dipakai Agent ketika pertanyaan menyangkut isi dokumen yang sudah diindeks.
"""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from backend.database import SessionLocal
from backend.services.document_service import filter_relevant, search_similar_chunks
from backend.services.embedding_service import EmbeddingError
from backend.tools import ToolInvocation, record

logger = logging.getLogger(__name__)

# Potongan dokumen dibungkus penanda agar model dapat membedakan mana data
# dan mana instruksi (PRD §18 - Prompt Injection). System prompt pada
# agent.py melarang model menuruti perintah yang muncul di dalam blok ini.
TEMPLATE_POTONGAN = "[sumber: {filename} #bagian-{index}]\n{isi}"


@tool("RAG_Search")
async def rag_search(query: str) -> str:
    """Cari informasi di dalam dokumen internal yang sudah diunggah pengguna.

    Gunakan untuk pertanyaan mengenai isi dokumen, kebijakan, peraturan,
    panduan, atau prosedur tertulis.

    Args:
        query: Pertanyaan atau kata kunci yang ingin dicari di dokumen.
    """
    db = SessionLocal()
    try:
        potongan = filter_relevant(await search_similar_chunks(db, query))
    except EmbeddingError as exc:
        record(ToolInvocation("RAG_Search", ok=False, detail=str(exc)))
        return f"Pencarian dokumen gagal: {exc}"
    finally:
        db.close()

    if not potongan:
        record(ToolInvocation("RAG_Search", ok=True, detail="tidak ada dokumen cocok"))
        return (
            "Tidak ada dokumen yang cocok dengan pertanyaan itu. "
            "Sampaikan kepada pengguna bahwa informasinya tidak ditemukan."
        )

    record(ToolInvocation("RAG_Search", ok=True, sources=potongan))
    logger.info("RAG_Search '%s' -> %d potongan", query, len(potongan))

    return "\n\n".join(
        TEMPLATE_POTONGAN.format(
            filename=p.filename,
            index=p.metadata.get("chunk_index", 0),
            isi=p.content,
        )
        for p in potongan
    )
