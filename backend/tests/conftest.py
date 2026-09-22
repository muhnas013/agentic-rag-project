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
from backend.models import ChatHistory, Document, User


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
def client_anonim(embedding_tiruan):
    """TestClient tanpa token — untuk menguji penolakan autentikasi."""
    with TestClient(main_module.app) as c:
        yield c


def _token(c, username, password):
    r = c.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login {username} gagal: {r.text}"
    return r.json()["access_token"]


@pytest.fixture
def client(client_anonim):
    """TestClient yang sudah masuk sebagai admin bawaan.

    Sebagian besar uji endpoint menyoal perilaku fiturnya, bukan lapisan
    autentikasi; memakai admin membuat uji itu tetap ringkas. Penolakan
    autentikasi dan otorisasi diuji tersendiri di `test_auth.py`.
    """
    token = _token(client_anonim, settings.admin_username, settings.admin_password)
    client_anonim.headers.update({"Authorization": f"Bearer {token}"})
    return client_anonim


@pytest.fixture
def buat_pengguna(client):
    """Buat akun dengan peran tertentu, lalu kembalikan TestClient miliknya."""
    dibuat = []

    def buat(username, role, password="rahasia123"):
        r = client.post(
            "/auth/users", json={"username": username, "password": password, "role": role}
        )
        assert r.status_code in (200, 409), r.text
        dibuat.append(username)

        c = TestClient(main_module.app)
        c.headers.update({"Authorization": f"Bearer {_token(c, username, password)}"})
        return c

    yield buat

    db = SessionLocal()
    try:
        for username in dibuat:
            db.query(User).filter(User.username == username).delete()
        db.commit()
    finally:
        db.close()


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
