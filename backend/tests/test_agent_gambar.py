"""Uji penjaga pertanyaan tentang gambar (B-31 dan B-32).

Agent dan modelnya diganti tiruan supaya perilakunya dapat diuji tanpa
memanggil LLM: yang diperiksa di sini keputusan alurnya — kapan percobaan
ulang dijalankan dan hasil mana yang dipakai — bukan mutu jawaban model.
"""

import asyncio
from types import SimpleNamespace

import pytest

from backend import agent as agent_module
from backend.config import settings
from backend.tools import ToolInvocation, record


class AgenPalsu:
    """Pengganti agent LangChain yang membalas jawaban tetap.

    Bila `tool` diisi, pemanggilan tool dicatat ke jejak — persis seperti
    yang dilakukan tool sungguhan lewat `record()`.
    """

    def __init__(self, jawaban: str, tool: str | None = None):
        self._jawaban = jawaban
        self._tool = tool

    async def ainvoke(self, _):
        if self._tool:
            record(ToolInvocation(self._tool, ok=True))
        return {"messages": [SimpleNamespace(content=self._jawaban)]}


@pytest.fixture
def gambar_ada(tmp_path, monkeypatch):
    """Satu gambar di folder unggahan."""
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    (tmp_path / "abc123__ktp.jpg").write_bytes(b"\xff\xd8\xff")
    return tmp_path


def pasang_agen(monkeypatch, *berurutan: AgenPalsu):
    """Setiap pemanggilan `build_agent` mengembalikan tiruan berikutnya."""
    sisa = list(berurutan)

    def build_agent(*_a, **_k):
        return sisa.pop(0) if len(sisa) > 1 else sisa[0]

    monkeypatch.setattr(agent_module, "build_agent", build_agent)


class TestMenyangkutGambar:
    def test_nama_berkas_disebut(self):
        assert agent_module._menyangkut_gambar("isi ktp.jpg apa?", ["ktp.jpg"])

    def test_kata_umum_dikenali(self):
        for q in ["apa isi foto tadi", "baca struk itu", "gambar tersebut apa"]:
            assert agent_module._menyangkut_gambar(q, ["ktp.jpg"]), q

    def test_pertanyaan_lain_tidak_ikut(self):
        assert not agent_module._menyangkut_gambar(
            "berapa pegawai di bagian Keuangan?", ["ktp.jpg"]
        )


class TestUlangTanpaRiwayat:
    """B-32: jawaban yang ditiru dari riwayat tidak boleh dibiarkan.

    Riwayat ada untuk memahami maksud pertanyaan, tetapi pada model kecil ia
    juga menjadi contoh yang ditiru. Sekali sebuah pertanyaan dijawab
    "tidak ditemukan", jawaban itu tersimpan dan ditiru pada giliran
    berikutnya — kegagalannya berputar menguatkan diri sendiri.
    """

    RIWAYAT = [
        {"role": "user", "content": "siapa nama di gambar ktp.jpg?"},
        {"role": "assistant", "content": "Maaf, tidak dapat ditemukan."},
    ]

    def test_jawaban_tanpa_tool_diulang_dan_diganti(
        self, monkeypatch, gambar_ada
    ):
        pasang_agen(
            monkeypatch,
            AgenPalsu("Maaf, tidak dapat ditemukan."),          # meniru riwayat
            AgenPalsu("Namanya MIRA SETIAWAN.", tool="Image_OCR"),  # ulangan
        )
        hasil = asyncio.run(agent_module.run_agent(
            "siapa nama di gambar ktp.jpg?", history=self.RIWAYAT
        ))
        assert "MIRA" in hasil.answer
        assert hasil.tool_used == "Image_OCR"

    def test_ulangan_yang_juga_tanpa_tool_tidak_dipakai(
        self, monkeypatch, gambar_ada
    ):
        """Menukar satu tebakan dengan tebakan lain tidak memperbaiki apa pun."""
        pasang_agen(
            monkeypatch,
            AgenPalsu("Jawaban pertama."),
            AgenPalsu("Jawaban kedua, juga tanpa tool."),
        )
        hasil = asyncio.run(agent_module.run_agent(
            "siapa nama di gambar ktp.jpg?", history=self.RIWAYAT
        ))
        assert hasil.answer == "Jawaban pertama."

    def test_tanpa_riwayat_tidak_perlu_diulang(self, monkeypatch, gambar_ada):
        """Tanpa riwayat tidak ada yang bisa ditiru, jadi tidak ada yang
        perlu diperbaiki — dan satu panggilan LLM tidak dibuang percuma."""
        pasang_agen(monkeypatch, AgenPalsu("Jawaban langsung."))
        hasil = asyncio.run(agent_module.run_agent("siapa nama di gambar ktp.jpg?"))
        assert hasil.answer == "Jawaban langsung."

    def test_pertanyaan_bukan_gambar_tidak_diulang(
        self, monkeypatch, gambar_ada
    ):
        pasang_agen(monkeypatch, AgenPalsu("Ada 12 pegawai."))
        hasil = asyncio.run(agent_module.run_agent(
            "berapa pegawai di bagian Keuangan?", history=self.RIWAYAT
        ))
        assert hasil.answer == "Ada 12 pegawai."

    def test_tanpa_gambar_terunggah_tidak_diulang(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(settings, "upload_dir", tmp_path)  # folder kosong
        pasang_agen(monkeypatch, AgenPalsu("Tidak ada gambar."))
        hasil = asyncio.run(agent_module.run_agent(
            "apa isi foto tadi?", history=self.RIWAYAT
        ))
        assert hasil.answer == "Tidak ada gambar."


class TestAturanRiwayatDiSystemPrompt:
    """Instruksi ini sendiri tidak cukup — B-32 membuktikan ia kalah oleh
    riwayat yang memuat beberapa penolakan berturut-turut — tetapi ia lapis
    pertama yang murah, dan penghapusannya tanpa sengaja harus ketahuan."""

    def test_melarang_menyalin_jawaban_lama(self):
        assert "BUKAN sumber" in agent_module.SYSTEM_PROMPT
