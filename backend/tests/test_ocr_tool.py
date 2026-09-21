"""Uji pemeriksaan path OCR Tool.

Path gambar datang dari LLM, jadi diperlakukan sebagai masukan tidak
tepercaya walaupun sumbernya model sendiri.
"""

import pytest

from backend.config import settings
from backend.tools.ocr_tool import resolve_image_path


@pytest.fixture
def gambar(tmp_path, monkeypatch):
    """Folder unggahan sementara berisi satu berkas gambar."""
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    # Disimpan dengan pola nyata: <uuid>__<nama asli>.
    berkas = tmp_path / "abc123__struk.png"
    berkas.write_bytes(b"\x89PNG\r\n\x1a\n")
    return berkas


def test_ditemukan_lewat_nama_asli(gambar):
    """Pengguna menyebut "struk.png", di disk namanya berawalan UUID."""
    assert resolve_image_path("struk.png").name == "abc123__struk.png"


def test_unggahan_terbaru_yang_dipakai(gambar, tmp_path):
    """Dua unggahan bernama sama: yang paling baru yang dibaca."""
    import os, time
    baru = tmp_path / "def456__struk.png"
    baru.write_bytes(b"\x89PNG\r\n\x1a\n")
    os.utime(baru, (time.time() + 10, time.time() + 10))
    assert resolve_image_path("struk.png").name == "def456__struk.png"


def test_path_traversal_tidak_bisa_keluar_folder(gambar):
    """'../../etc/passwd' hanya diambil nama berkasnya, jadi tidak pernah keluar."""
    with pytest.raises(FileNotFoundError):
        resolve_image_path("../../etc/passwd")


def test_berkas_tidak_ada_memberi_galat_jelas(gambar):
    with pytest.raises(FileNotFoundError, match="tidak ditemukan"):
        resolve_image_path("entah.png")


def test_ekstensi_bukan_gambar_ditolak(gambar, tmp_path):
    (tmp_path / "xyz789__catatan.txt").write_text("halo")
    with pytest.raises(ValueError, match="bukan gambar"):
        resolve_image_path("catatan.txt")


def test_tool_melaporkan_ocr_belum_siap(gambar):
    from backend.tools.ocr_tool import image_ocr

    hasil = image_ocr.invoke({"image_path": "struk.png"})
    assert "belum tersedia" in hasil.lower()
