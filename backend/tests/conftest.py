"""Perkakas bersama untuk uji API.

Embedding dan Agent diganti tiruan supaya uji endpoint deterministik dan
cepat: yang diperiksa di sini adalah kontrak HTTP — status, bentuk balasan,
validasi, dan penanganan galat — bukan mutu model. Integrasi sungguhan
diuji terpisah lewat matriks PRD §17 terhadap sistem yang berjalan.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.config import settings
from backend.database import SessionLocal
from backend.models import ChatHistory, Document


@pytest.fixture
def embedding_tiruan(monkeypatch):
    """Vektor deterministik tanpa memanggil model apa pun."""
    from backend.services import document_service as ds

    def vektor(teks: str) -> list[float]:
        v = [0.0] * settings.embedding_dim
        for i, ch in enumerate(teks[:64]):
            v[(ord(ch) * (i + 1)) % settings.embedding_dim] += 1.0
        panjang = sum(x * x for x in v) ** 0.5 or 1.0
        return [x / panjang for x in v]

    async def embed_texts(daftar):
        return [vektor(t) for t in daftar]

    async def embed_query(teks):
        return vektor(teks)

    monkeypatch.setattr(ds, "embed_texts", embed_texts)
    monkeypatch.setattr(ds, "embed_query", embed_query)


@pytest.fixture
def client(embedding_tiruan):
    """TestClient dengan lifespan aktif, sehingga tabel dipastikan ada."""
    with TestClient(main_module.app) as c:
        yield c


@pytest.fixture
def nama_berkas():
    """Nama unik supaya baris uji tidak bertabrakan dengan data lain."""
    return f"uji-{uuid.uuid4().hex[:8]}.txt"


@pytest.fixture
def sesi():
    return f"uji-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def bersihkan(nama_berkas, sesi):
    """Hapus jejak tiap uji, apa pun hasilnya."""
    yield
    db = SessionLocal()
    try:
        db.query(Document).filter(Document.filename == nama_berkas).delete()
        db.query(ChatHistory).filter(ChatHistory.session_id == sesi).delete()
        db.commit()
    finally:
        db.close()
