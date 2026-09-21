"""Konfigurasi aplikasi, dibaca dari .env lewat pydantic-settings.

Semua nilai yang bisa berubah antar lingkungan hidup di sini. Tidak ada
kredensial, nama model, atau dimensi vektor yang ditulis mati di kode lain.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/config.py -> backend/ -> root project
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class LLMProvider(str, Enum):
    """Penyedia LLM. `ollama` adalah target akhir sesuai PRD §4.2."""

    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class EmbeddingProvider(str, Enum):
    """Penyedia embedding.

    `hash_stub` hanya untuk pengembangan: embedding deterministik berbasis
    hashing sehingga pipeline RAG dapat diuji tanpa model apa pun. Kualitas
    semantiknya rendah dan tidak mewakili mutu retrieval sebenarnya.
    """

    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"
    HASH_STUB = "hash_stub"


def _split_csv(value: str | list[str]) -> list[str]:
    """Ubah "a,b , c" menjadi ["a", "b", "c"]."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


# NoDecode mematikan penguraian JSON bawaan pydantic-settings, sehingga daftar
# pada .env boleh ditulis dipisah koma seperti contoh PRD §19 — bukan sebagai
# array JSON. Tanpa ini, pembacaan .env gagal sebelum validator sempat jalan.
CSVList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplikasi ---
    app_env: str = "development"
    app_name: str = "Agentic RAG"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Database ---
    database_url: str
    sql_agent_database_url: str
    sql_agent_allowed_tables: CSVList = Field(default_factory=list)
    sql_agent_query_timeout: int = 10
    sql_agent_max_rows: int = 100

    # --- Provider AI ---
    llm_provider: LLMProvider = LLMProvider.OLLAMA
    embedding_provider: EmbeddingProvider = EmbeddingProvider.OLLAMA

    llm_api_base_url: str = ""
    llm_api_model: str = ""
    llm_api_key: str = ""

    embedding_api_base_url: str = ""
    embedding_api_model: str = ""
    embedding_api_key: str = ""

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen2.5:7b-instruct-q4_K_M"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout: int = 120
    ollama_num_ctx: int = 8192

    # Provider API dapat membalas 503/429 secara sporadis; percobaan
    # ulang dilakukan dengan jeda menaik sebelum menyerah.
    llm_max_retries: int = 8

    # Dimensi kolom VECTOR mengikuti nilai ini, tidak ditulis mati (D-02b).
    embedding_dim: int = 768

    # --- RAG ---
    chunk_size: int = 800
    chunk_overlap: int = 120
    rag_top_k: int = 4
    rag_min_score_ratio: float = 0.5

    # Potongan dokumen yang memuat pola pengambilalihan peran
    # disingkirkan dari hasil pencarian (PRD §18).
    rag_quarantine_suspicious: bool = True

    # --- Upload ---
    upload_dir: Path = PROJECT_ROOT / "storage" / "uploads"
    processed_dir: Path = PROJECT_ROOT / "storage" / "processed"
    max_upload_size_mb: int = 20
    allowed_doc_extensions: CSVList = Field(default_factory=list)
    allowed_image_extensions: CSVList = Field(default_factory=list)

    # --- OCR (dipakai mulai Fase 5) ---
    ocr_lang: str = "en"
    ocr_use_gpu: bool = False

    # --- Security ---
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- CORS ---
    cors_origins: CSVList = Field(default_factory=list)

    @field_validator(
        "sql_agent_allowed_tables",
        "allowed_doc_extensions",
        "allowed_image_extensions",
        "cors_origins",
        mode="before",
    )
    @classmethod
    def _parse_csv(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        return _split_csv(value)  # type: ignore[arg-type]

    @field_validator("allowed_doc_extensions", "allowed_image_extensions")
    @classmethod
    def _normalise_extensions(cls, value: list[str]) -> list[str]:
        """Samakan bentuk ekstensi menjadi huruf kecil berawalan titik."""
        return [
            item.lower() if item.startswith(".") else f".{item.lower()}"
            for item in value
        ]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_extensions(self) -> list[str]:
        return [*self.allowed_doc_extensions, *self.allowed_image_extensions]

    @property
    def llm_model_name(self) -> str:
        """Nama model LLM yang aktif, apa pun providernya."""
        if self.llm_provider is LLMProvider.OLLAMA:
            return self.ollama_llm_model
        return self.llm_api_model

    @property
    def embedding_model_name(self) -> str:
        """Nama model embedding yang aktif, apa pun providernya."""
        if self.embedding_provider is EmbeddingProvider.OLLAMA:
            return self.ollama_embedding_model
        if self.embedding_provider is EmbeddingProvider.OPENAI_COMPATIBLE:
            return self.embedding_api_model
        return "hash_stub"


@lru_cache
def get_settings() -> Settings:
    """Settings dibaca sekali lalu dipakai ulang selama proses hidup."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
