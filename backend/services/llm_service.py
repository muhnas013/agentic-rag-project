"""Pembuatan model LLM. Satu provider saja: Ollama, sesuai PRD §4.2.

Dikembalikan sebagai `BaseChatModel` milik LangChain sehingga `agent.py`
memanggil LLM lewat satu jalur saja (keputusan D-11).

`embedding_service.py` sengaja tetap memakai httpx langsung: `hash_stub`
tidak punya padanan di LangChain, dan pemeriksaan dimensi vektor di sana
lebih berguna daripada keseragaman lapisan.
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel

from backend.config import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Provider LLM tidak dapat disiapkan atau dipanggil."""


def get_chat_model(temperature: float = 0.2) -> BaseChatModel:
    """Bangun model LLM Ollama sesuai setelan `.env`."""
    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_llm_model,
        temperature=temperature,
        # num_ctx menjaga KV cache tetap kecil (keputusan D-02).
        num_ctx=settings.ollama_num_ctx,
    )
