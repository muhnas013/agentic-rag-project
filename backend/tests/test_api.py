"""Uji kontrak endpoint (PRD §20)."""

import io

import pytest

from backend import main as main_module
from backend.agent import AgentResult
from backend.tools import ToolInvocation

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"


class TestHealth:
    def test_melaporkan_database_dan_model(self, client):
        r = client.get("/health")
        assert r.status_code == 200

        data = r.json()
        assert data["status"] in ("ok", "degraded")
        assert data["database"] is True
        assert data["vector_extension"] is True
        assert data["embedding_dim"] > 0
        # Nama provider berguna saat menelusuri jawaban yang aneh.
        assert data["llm_provider"] and data["embedding_provider"]


class TestDokumen:
    def test_tambah_teks_lalu_muncul_di_daftar(self, client, nama_berkas):
        r = client.post(
            "/documents",
            json={"filename": nama_berkas, "content": "Isi dokumen uji yang cukup panjang."},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "processed"
        assert r.json()["chunks"] >= 1

        daftar = client.get("/documents").json()
        assert nama_berkas in [d["filename"] for d in daftar]

    def test_isi_kosong_ditolak_validasi(self, client, nama_berkas):
        r = client.post("/documents", json={"filename": nama_berkas, "content": ""})
        assert r.status_code == 422

    def test_unggah_ulang_mengganti_bukan_menumpuk(self, client, nama_berkas):
        for _ in range(2):
            client.post("/documents", json={"filename": nama_berkas, "content": "isi tetap"})

        daftar = client.get("/documents").json()
        cocok = [d for d in daftar if d["filename"] == nama_berkas]
        assert len(cocok) == 1
        assert cocok[0]["chunks"] == 1


class TestUpload:
    def test_ekstensi_di_luar_allowlist_ditolak(self, client):
        r = client.post("/upload", files={"file": ("jahat.exe", b"MZ\x90\x00", "application/octet-stream")})
        assert r.status_code == 400
        assert "tidak diizinkan" in r.json()["detail"]

    def test_signature_tidak_cocok_ditolak(self, client):
        """PNG yang dinamai .pdf harus tertangkap sebelum disimpan."""
        r = client.post("/upload", files={"file": ("palsu.pdf", PNG, "application/pdf")})
        assert r.status_code == 400

    def test_berkas_kosong_ditolak(self, client):
        r = client.post("/upload", files={"file": ("kosong.txt", b"", "text/plain")})
        assert r.status_code == 400

    def test_gambar_disimpan_tanpa_diindeks(self, client):
        """Gambar menunggu Agent memanggil OCR, bukan diolah saat unggah."""
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        r = client.post("/upload", files={"file": ("titik.png", png, "image/png")})
        assert r.status_code == 200
        assert r.json()["status"] == "stored"
        assert r.json()["chunks"] == 0


class TestQuery:
    def test_mengembalikan_potongan_dengan_skor(self, client, nama_berkas):
        client.post("/documents", json={"filename": nama_berkas, "content": "kebijakan retensi arsip"})

        r = client.post("/query", json={"query": "retensi arsip", "top_k": 3})
        assert r.status_code == 200

        hasil = r.json()["results"]
        assert hasil, "pencarian tidak mengembalikan apa pun"
        assert all("filename" in h and "score" in h for h in hasil)

    def test_top_k_di_luar_batas_ditolak(self, client):
        assert client.post("/query", json={"query": "x", "top_k": 0}).status_code == 422
        assert client.post("/query", json={"query": "x", "top_k": 99}).status_code == 422

    def test_pertanyaan_kosong_ditolak(self, client):
        assert client.post("/query", json={"query": ""}).status_code == 422


class TestChat:
    @pytest.fixture
    def agent_tiruan(self, monkeypatch):
        async def run_agent(question, history=None):
            return AgentResult(
                answer=f"jawaban untuk: {question}",
                tool_calls=[ToolInvocation("RAG_Search", ok=True)],
            )

        monkeypatch.setattr(main_module, "run_agent", run_agent)

    def test_menjawab_dan_menyimpan_riwayat(self, client, agent_tiruan, sesi):
        r = client.post("/chat", json={"session_id": sesi, "message": "apa kabar"})
        assert r.status_code == 200
        assert r.json()["tool_used"] == "RAG_Search"

        riwayat = client.get("/chat/history", params={"session_id": sesi}).json()
        peran = [m["role"] for m in riwayat["messages"]]
        assert peran == ["user", "assistant"], "pesan pengguna dan jawaban harus tersimpan berurutan"

    def test_galat_provider_menjadi_503(self, client, monkeypatch, sesi):
        from backend.services.llm_service import LLMError

        async def gagal(question, history=None):
            raise LLMError("Ollama tidak dapat dihubungi")

        monkeypatch.setattr(main_module, "run_agent", gagal)

        r = client.post("/chat", json={"session_id": sesi, "message": "halo"})
        assert r.status_code == 503
        assert "Ollama" in r.json()["detail"]

    def test_riwayat_tidak_ikut_tersimpan_saat_gagal(self, client, monkeypatch, sesi):
        """Pertanyaan yang gagal dijawab tidak boleh mengotori riwayat."""
        from backend.services.llm_service import LLMError

        async def gagal(question, history=None):
            raise LLMError("gagal")

        monkeypatch.setattr(main_module, "run_agent", gagal)
        client.post("/chat", json={"session_id": sesi, "message": "halo"})

        riwayat = client.get("/chat/history", params={"session_id": sesi}).json()
        assert riwayat["messages"] == []

    def test_session_id_kosong_ditolak(self, client):
        assert client.post("/chat", json={"session_id": "", "message": "x"}).status_code == 422

    def test_pesan_kosong_ditolak(self, client, sesi):
        assert client.post("/chat", json={"session_id": sesi, "message": ""}).status_code == 422


class TestRiwayat:
    def test_sesi_baru_menghasilkan_daftar_kosong(self, client, sesi):
        r = client.get("/chat/history", params={"session_id": sesi})
        assert r.status_code == 200
        assert r.json()["messages"] == []

    def test_session_id_wajib(self, client):
        assert client.get("/chat/history").status_code == 422

    def test_limit_di_luar_batas_ditolak(self, client, sesi):
        r = client.get("/chat/history", params={"session_id": sesi, "limit": 9999})
        assert r.status_code == 422


class TestDaftarSesi:
    """Daftar percakapan untuk sidebar (PRD §15 - Chat history)."""

    @pytest.fixture
    def agent_tiruan(self, monkeypatch):
        async def run_agent(question, history=None):
            return AgentResult(answer=f"jawaban: {question}", tool_calls=[])

        monkeypatch.setattr(main_module, "run_agent", run_agent)

    @pytest.fixture
    def dua_sesi(self, client, agent_tiruan):
        import uuid

        a, b = f"s-{uuid.uuid4().hex[:8]}", f"s-{uuid.uuid4().hex[:8]}"
        client.post("/chat", json={"session_id": a, "message": "pertanyaan pertama sesi A"})
        client.post("/chat", json={"session_id": b, "message": "pertanyaan pertama sesi B"})
        yield a, b

        from backend.database import SessionLocal
        from backend.models import ChatHistory

        db = SessionLocal()
        try:
            db.query(ChatHistory).filter(ChatHistory.session_id.in_([a, b])).delete(
                synchronize_session=False
            )
            db.commit()
        finally:
            db.close()

    def test_judul_diambil_dari_pesan_pertama_pengguna(self, client, dua_sesi):
        a, _ = dua_sesi
        daftar = client.get("/chat/sessions").json()
        cocok = [s for s in daftar if s["session_id"] == a]
        assert cocok and cocok[0]["judul"] == "pertanyaan pertama sesi A"

    def test_menghitung_pesan_pengguna_dan_jawaban(self, client, dua_sesi):
        a, _ = dua_sesi
        cocok = [s for s in client.get("/chat/sessions").json() if s["session_id"] == a]
        assert cocok[0]["jumlah_pesan"] == 2

    def test_terbaru_lebih_dulu(self, client, dua_sesi):
        a, b = dua_sesi
        urut = [s["session_id"] for s in client.get("/chat/sessions").json()]
        assert urut.index(b) < urut.index(a), "sesi yang lebih baru harus di atas"

    def test_judul_panjang_dipotong(self, client, agent_tiruan, sesi):
        panjang = "kata " * 40
        client.post("/chat", json={"session_id": sesi, "message": panjang})
        cocok = [s for s in client.get("/chat/sessions").json() if s["session_id"] == sesi]
        assert cocok[0]["judul"].endswith("…")
        assert len(cocok[0]["judul"]) <= main_module.PANJANG_JUDUL + 1

    def test_tanpa_token_ditolak(self, client_anonim):
        assert client_anonim.get("/chat/sessions").status_code == 401


class TestHapusSesi:
    @pytest.fixture
    def agent_tiruan(self, monkeypatch):
        async def run_agent(question, history=None):
            return AgentResult(answer="ok", tool_calls=[])

        monkeypatch.setattr(main_module, "run_agent", run_agent)

    def test_menghapus_seluruh_pesannya(self, client, agent_tiruan, sesi):
        client.post("/chat", json={"session_id": sesi, "message": "halo"})
        assert client.delete(f"/chat/sessions/{sesi}").status_code == 204

        riwayat = client.get("/chat/history", params={"session_id": sesi}).json()
        assert riwayat["messages"] == []

    def test_sesi_tidak_ada_menghasilkan_404(self, client):
        assert client.delete("/chat/sessions/tidak-pernah-ada").status_code == 404

    def test_read_only_tidak_boleh_menghapus(self, buat_pengguna, client, agent_tiruan, sesi):
        client.post("/chat", json={"session_id": sesi, "message": "halo"})
        c = buat_pengguna("uji_hapus", "READ_ONLY")
        assert c.delete(f"/chat/sessions/{sesi}").status_code == 403
