"""Pembuatan embedding, dengan provider yang bisa ditukar lewat .env.

Dua provider tersedia:

- `ollama`    sesuai PRD §4.2, satu-satunya provider untuk pemakaian nyata.
- `hash_stub` embedding deterministik tanpa model, KHUSUS pengembangan.

Keduanya mengembalikan vektor sepanjang `EMBEDDING_DIM` dan sudah
dinormalisasi, sehingga jarak cosine pada pgvector langsung bermakna.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod

import httpx

from backend.config import EmbeddingProvider, settings

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Gagal membuat embedding."""


def _normalise(vector: list[float]) -> list[float]:
    """Jadikan panjang vektor 1 agar jarak cosine hanya menilai arah."""
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class EmbeddingBackend(ABC):
    """Kontrak yang harus dipenuhi setiap provider embedding."""

    name: str

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Ubah sekumpulan teks menjadi vektor, urutannya dipertahankan."""

    async def embed_one(self, text: str) -> list[float]:
        vectors = await self.embed([text])
        return vectors[0]


class OllamaEmbedding(EmbeddingBackend):
    """Provider sesuai PRD: Ollama di host (keputusan D-03)."""

    name = "ollama"

    def __init__(self) -> None:
        self._url = f"{settings.ollama_base_url.rstrip('/')}/api/embed"
        self._model = settings.ollama_embedding_model
        self._timeout = settings.ollama_timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self._model, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise EmbeddingError(
                f"Gagal memanggil Ollama di {self._url}: {exc}. "
                "Pastikan Ollama berjalan dan model "
                f"'{self._model}' sudah diunduh."
            ) from exc

        vectors = data.get("embeddings")
        if not vectors:
            raise EmbeddingError(f"Ollama tidak mengembalikan embedding: {data}")
        return [_normalise(vector) for vector in vectors]


class HashStubEmbedding(EmbeddingBackend):
    """Embedding deterministik tanpa model — hanya untuk pengembangan.

    Setiap kata dipetakan ke satu dimensi lewat hash, lalu dihitung
    frekuensinya. Hasilnya menangkap kesamaan kata, bukan kesamaan makna:
    "mobil" dan "kendaraan" dianggap tidak berhubungan sama sekali.

    Gunanya adalah membuat seluruh pipeline RAG (chunking, penyimpanan,
    pencarian pgvector, penyusunan konteks) dapat diuji sebelum model
    embedding tersedia. Jangan dipakai menilai mutu retrieval.
    """

    name = "hash_stub"
    _token_pattern = re.compile(r"\w+", re.UNICODE)

    def __init__(self) -> None:
        self._dim = settings.embedding_dim

    def _embed_sync(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for token in self._token_pattern.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % self._dim
            vector[index] += 1.0
        return _normalise(vector)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_sync(text) for text in texts]


_BACKENDS: dict[EmbeddingProvider, type[EmbeddingBackend]] = {
    EmbeddingProvider.OLLAMA: OllamaEmbedding,
    EmbeddingProvider.HASH_STUB: HashStubEmbedding,
}


def get_embedding_backend() -> EmbeddingBackend:
    """Bangun provider embedding sesuai EMBEDDING_PROVIDER di .env."""
    backend_cls = _BACKENDS[settings.embedding_provider]
    backend = backend_cls()
    if settings.embedding_provider is EmbeddingProvider.HASH_STUB:
        logger.warning(
            "EMBEDDING_PROVIDER=hash_stub — embedding dibuat tanpa model. "
            "Pipeline RAG dapat diuji, tetapi mutu retrieval tidak berarti."
        )
    return backend


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embedding untuk potongan dokumen, sekaligus memeriksa dimensinya."""
    if not texts:
        return []
    vectors = await get_embedding_backend().embed(texts)
    _assert_dimension(vectors[0])
    return vectors


async def embed_query(text: str) -> list[float]:
    """Embedding untuk pertanyaan pengguna."""
    vector = await get_embedding_backend().embed_one(text)
    _assert_dimension(vector)
    return vector


def _assert_dimension(vector: list[float]) -> None:
    """Ketidakcocokan dimensi harus ketahuan di sini, bukan saat INSERT.

    Kolom `documents.embedding` dibuat dengan lebar EMBEDDING_DIM. Bila model
    embedding diganti tanpa memperbarui nilai itu, pesan galat dari PostgreSQL
    sulit dilacak sampai ke penyebabnya.
    """
    if len(vector) != settings.embedding_dim:
        raise EmbeddingError(
            f"Model '{settings.embedding_model_name}' menghasilkan "
            f"{len(vector)} dimensi, sedangkan EMBEDDING_DIM={settings.embedding_dim}. "
            "Samakan EMBEDDING_DIM di .env lalu migrasikan kolom "
            "documents.embedding dan lakukan embedding ulang."
        )
