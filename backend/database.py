"""Koneksi database.

Ada dua engine terpisah sesuai keputusan D-05 (PRD §18):

- `engine`           koneksi aplikasi, hak baca-tulis penuh.
- `sql_agent_engine` koneksi khusus SQL Tool, memakai user read-only yang
                     dibuat skrip init PostgreSQL. Dipakai mulai Fase 5.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """Base class untuk seluruh model SQLAlchemy."""


engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # koneksi basi dibuang, bukan dipakai lalu gagal
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _build_sql_agent_engine() -> Engine:
    """Engine read-only untuk SQL Tool.

    Timeout dipasang lagi di sisi klien walaupun sudah ada `statement_timeout`
    pada role PostgreSQL, agar batasnya tetap berlaku bila kredensial diganti.
    """
    return create_engine(
        settings.sql_agent_database_url,
        pool_pre_ping=True,
        future=True,
        connect_args={
            "options": f"-c statement_timeout={settings.sql_agent_query_timeout * 1000}",
        },
    )


sql_agent_engine: Engine = _build_sql_agent_engine()
SQLAgentSessionLocal = sessionmaker(bind=sql_agent_engine, autoflush=False)


def get_db() -> Iterator[Session]:
    """Dependency FastAPI: satu session per request, selalu ditutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_vector_extension() -> None:
    """Aktifkan extension pgvector (PRD §7.2).

    Skrip init container sudah menjalankannya, tetapi pemanggilan ini membuat
    aplikasi tetap benar bila dijalankan terhadap database yang sudah ada.
    """
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def init_database() -> None:
    """Siapkan extension lalu buat tabel yang belum ada.

    Cukup untuk MVP. Bila skema berubah setelah ada data produksi, ganti
    dengan migrasi Alembic.
    """
    from backend import models  # noqa: F401  -- registrasi model ke metadata

    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)


def check_database_connection() -> bool:
    """Dipakai endpoint /health."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
