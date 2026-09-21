"""Model tabel sesuai PRD §7."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.config import settings
from backend.database import Base

# Peran pesan yang dikenali (PRD §7.1).
CHAT_ROLES = ("user", "assistant", "system", "tool")


class ChatHistory(Base):
    """Riwayat percakapan, satu baris per pesan (PRD §7.1)."""

    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    def __repr__(self) -> str:
        return f"<ChatHistory id={self.id} session={self.session_id} role={self.role}>"


class Document(Base):
    """Satu potongan (chunk) dokumen beserta embedding-nya (PRD §7.2).

    Satu file menghasilkan banyak baris; asal file dan nomor potongan
    disimpan di kolom `metadata`.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Dimensi dibaca dari EMBEDDING_DIM agar pindah model embedding tidak
    # memerlukan perubahan kode (keputusan D-02b).
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )

    # Atribut tidak bisa bernama `metadata`: nama itu dipakai SQLAlchemy
    # pada Declarative Base. Nama kolom di database tetap "metadata"
    # supaya sama persis dengan PRD §7.2.
    doc_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    __table_args__ = (
        # HNSW mempercepat pencarian kemiripan. Jarak cosine dipakai karena
        # embedding dinormalisasi panjangnya, sehingga arah vektor yang
        # menentukan kemiripan, bukan besarannya.
        Index(
            "ix_documents_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r}>"
