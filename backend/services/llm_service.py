"""Pembuatan model LLM, dengan provider yang bisa ditukar lewat `.env`.

Dua provider tersedia:

- `ollama`            sesuai PRD §4.2, dipakai setelah model lokal diunduh.
- `openai_compatible` layanan API yang meniru /v1/chat/completions.

Keduanya dikembalikan sebagai `BaseChatModel` milik LangChain, sehingga
`agent.py` tidak perlu tahu provider mana yang sedang aktif — dan tidak ada
dua jalur pemanggilan LLM yang harus dirawat bersamaan (keputusan D-11).

`embedding_service.py` sengaja tetap memakai httpx langsung: `hash_stub`
tidak punya padanan di LangChain, dan pemeriksaan dimensi vektor di sana
lebih berguna daripada keseragaman lapisan.
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel

from backend.config import LLMProvider, settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Provider LLM tidak dapat disiapkan atau dipanggil."""


def _build_openai_compatible(temperature: float) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    if not settings.llm_api_base_url or not settings.llm_api_model:
        raise LLMError(
            "LLM_PROVIDER=openai_compatible membutuhkan LLM_API_BASE_URL "
            "dan LLM_API_MODEL di .env."
        )
    if not settings.llm_api_key:
        raise LLMError(
            "LLM_API_KEY masih kosong. Isi di .env, lalu jalankan "
            "`docker compose up -d backend` — `restart` tidak membaca ulang .env."
        )

    return ChatOpenAI(
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_api_model,
        temperature=temperature,
        timeout=settings.ollama_timeout,
        # Provider API bisa membalas 503 atau 429 secara sporadis; SDK-nya
        # mencoba ulang sendiri dengan jeda menaik sebelum menyerah.
        max_retries=settings.llm_max_retries,
    )


def _build_ollama(temperature: float) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_llm_model,
        temperature=temperature,
        # num_ctx menjaga KV cache tetap kecil (keputusan D-02).
        num_ctx=settings.ollama_num_ctx,
    )


def get_chat_model(temperature: float = 0.2) -> BaseChatModel:
    """Bangun model LLM sesuai `LLM_PROVIDER` di `.env`."""
    if settings.llm_provider is LLMProvider.OLLAMA:
        return _build_ollama(temperature)
    return _build_openai_compatible(temperature)
