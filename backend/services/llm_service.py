"""Pemanggilan LLM, dengan provider yang bisa ditukar lewat .env.

Dua provider tersedia:

- `ollama`            sesuai PRD §4.2, dipakai setelah model lokal diunduh.
- `openai_compatible` layanan API yang meniru /v1/chat/completions.

Balasan kedua provider diseragamkan menjadi `ChatResponse`, termasuk bagian
`tool_calls`, supaya Agent Orchestrator pada Fase 4 tidak perlu tahu provider
mana yang sedang aktif.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.config import LLMProvider, settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Gagal memanggil LLM."""


@dataclass
class ToolCall:
    """Permintaan pemanggilan tool dari model (dipakai mulai Fase 4)."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


def _parse_arguments(value: Any) -> dict[str, Any]:
    """Argumen tool datang sebagai string JSON di OpenAI, objek di Ollama."""
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        logger.warning("Argumen tool bukan JSON yang sah: %r", value)
        return {}
    return parsed if isinstance(parsed, dict) else {}


class LLMBackend(ABC):
    """Kontrak yang harus dipenuhi setiap provider LLM."""

    name: str

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> ChatResponse:
        """Kirim percakapan, kembalikan jawaban yang sudah diseragamkan."""

    @abstractmethod
    async def health(self) -> bool:
        """Periksa apakah provider dapat dihubungi."""


class OllamaLLM(LLMBackend):
    """Provider sesuai PRD: Ollama di host (keputusan D-03)."""

    name = "ollama"

    def __init__(self) -> None:
        self._base = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_llm_model
        self._timeout = settings.ollama_timeout

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            # num_ctx menjaga KV cache tetap kecil (keputusan D-02).
            "options": {
                "temperature": temperature,
                "num_ctx": settings.ollama_num_ctx,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise LLMError(
                f"Gagal memanggil Ollama di {self._base}: {exc}. "
                f"Pastikan Ollama berjalan dan model '{self._model}' sudah diunduh."
            ) from exc

        message = data.get("message", {})
        return ChatResponse(
            content=message.get("content", ""),
            tool_calls=[
                ToolCall(
                    id=str(index),
                    name=call["function"]["name"],
                    arguments=_parse_arguments(call["function"].get("arguments")),
                )
                for index, call in enumerate(message.get("tool_calls") or [])
            ],
            model=data.get("model", self._model),
            raw=data,
        )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self._base}/api/tags")
                response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False


class OpenAICompatibleLLM(LLMBackend):
    """Provider API yang meniru /v1/chat/completions.

    Dipakai selama model lokal belum diunduh. Nilai bawaannya mengarah ke
    Atria Dawn Preview, yang mendukung tool calling.
    """

    name = "openai_compatible"

    def __init__(self) -> None:
        if not settings.llm_api_base_url or not settings.llm_api_model:
            raise LLMError(
                "LLM_PROVIDER=openai_compatible membutuhkan LLM_API_BASE_URL "
                "dan LLM_API_MODEL di .env."
            )
        if not settings.llm_api_key:
            raise LLMError(
                "LLM_API_KEY masih kosong. Isi di .env, lalu jalankan ulang "
                "container backend."
            )
        self._base = settings.llm_api_base_url.rstrip("/")
        self._model = settings.llm_api_model
        self._key = settings.llm_api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}"}

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
                response = await client.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            # Status dikutip apa adanya supaya 401 (key salah) dan 429 (kena
            # batas laju) bisa dibedakan tanpa membaca log provider.
            raise LLMError(
                f"Provider LLM menolak permintaan "
                f"({exc.response.status_code}): {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Gagal memanggil provider LLM di {self._base}: {exc}") from exc

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Bentuk balasan tidak dikenali: {data}") from exc

        return ChatResponse(
            content=message.get("content") or "",
            tool_calls=[
                ToolCall(
                    id=call.get("id", str(index)),
                    name=call["function"]["name"],
                    arguments=_parse_arguments(call["function"].get("arguments")),
                )
                for index, call in enumerate(message.get("tool_calls") or [])
            ],
            model=data.get("model", self._model),
            raw=data,
        )

    async def health(self) -> bool:
        """Satu permintaan sependek mungkin, sekadar memastikan key diterima."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{self._base}/chat/completions",
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                    headers=self._headers,
                )
                response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("Health check provider LLM gagal: %s", exc)
            return False


_BACKENDS: dict[LLMProvider, type[LLMBackend]] = {
    LLMProvider.OLLAMA: OllamaLLM,
    LLMProvider.OPENAI_COMPATIBLE: OpenAICompatibleLLM,
}


def get_llm_backend() -> LLMBackend:
    """Bangun provider LLM sesuai LLM_PROVIDER di .env."""
    return _BACKENDS[settings.llm_provider]()


async def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.2,
) -> ChatResponse:
    return await get_llm_backend().chat(messages, tools=tools, temperature=temperature)
