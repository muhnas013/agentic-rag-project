"""Pembuatan model LLM. Satu provider saja: Ollama, sesuai PRD §4.2.

Dikembalikan sebagai `BaseChatModel` milik LangChain sehingga `agent.py`
memanggil LLM lewat satu jalur saja (keputusan D-11).

`embedding_service.py` sengaja tetap memakai httpx langsung: `hash_stub`
tidak punya padanan di LangChain, dan pemeriksaan dimensi vektor di sana
lebih berguna daripada keseragaman lapisan.
"""

from __future__ import annotations

import logging

import httpx
from langchain_core.language_models import BaseChatModel

from backend.config import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Provider LLM tidak dapat disiapkan atau dipanggil."""


def get_chat_model(temperature: float = 0.2, model: str | None = None) -> BaseChatModel:
    """Bangun model LLM Ollama.

    `model` menimpa `OLLAMA_LLM_MODEL` untuk satu pemanggilan saja. Pilihan
    model disampaikan sebagai argumen, bukan disimpan sebagai keadaan global,
    supaya dua permintaan yang berjalan bersamaan tidak saling menimpa
    pilihan satu sama lain — dan supaya `.env` tetap menjadi satu-satunya
    penentu nilai bawaannya.
    """
    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=model or settings.ollama_llm_model,
        temperature=temperature,
        # num_ctx menjaga KV cache tetap kecil (keputusan D-02).
        num_ctx=settings.ollama_num_ctx,
    )


def _model_embedding(nama: str, keluarga: str) -> bool:
    """Apakah model ini pembuat embedding, bukan model percakapan?

    Ollama tidak menandai keduanya secara eksplisit pada `/api/tags`, jadi
    penyaringannya bersandar pada dua petunjuk: nama yang sama dengan model
    embedding yang sedang dipakai, dan keluarga model berbasis BERT — yang
    dipakai hampir semua model embedding dan tidak satu pun model
    percakapan. Bila kelak ada yang lolos, gejalanya jelas dan tidak
    berbahaya: satu nama tambahan muncul di daftar pilihan, dan memilihnya
    menghasilkan galat dari Ollama.
    """
    dasar = nama.split(":", 1)[0]
    embedding = settings.ollama_embedding_model.split(":", 1)[0]
    return dasar == embedding or "bert" in keluarga.lower()


async def daftar_model_llm() -> list[str]:
    """Nama model percakapan yang tersedia di Ollama, terurut.

    Raises:
        LLMError: bila Ollama tidak dapat dihubungi.
    """
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            balasan = await client.get(url)
            balasan.raise_for_status()
            data = balasan.json()
    except httpx.HTTPError as exc:
        raise LLMError(
            f"Gagal membaca daftar model dari Ollama di {url}: {exc}. "
            "Pastikan Ollama berjalan."
        ) from exc

    nama = []
    for m in data.get("models", []):
        n = m.get("name") or m.get("model")
        if not n:
            continue
        keluarga = (m.get("details") or {}).get("family", "")
        if _model_embedding(n, keluarga):
            continue
        nama.append(n)
    return sorted(set(nama))
