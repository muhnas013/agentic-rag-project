"""Uji OCR Tool (PRD §8 dan §10).

Pemanggilan PaddleOCR yang sebenarnya diuji terpisah dengan gambar nyata;
di sini yang diuji adalah dua hal yang mudah salah dan mahal bila lolos:
pencarian berkas dari nama yang disebut pengguna, dan penyaringan baris
berkeyakinan rendah.
"""

import pytest

from backend.config import settings
from backend.tools import ocr_tool
from backend.tools.ocr_tool import (
    AMBANG_KEYAKINAN,
    baca_teks,
    resolve_image_path,
    susun_baris,
)


@pytest.fixture
def gambar(tmp_path, monkeypatch):
    """Folder unggahan sementara berisi satu gambar bernama pola nyata."""
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    berkas = tmp_path / "abc123__struk.png"
    berkas.write_bytes(b"\x89PNG\r\n\x1a\n")
    return berkas


class TestPencarianBerkas:
    def test_ditemukan_lewat_nama_asli(self, gambar):
        """Pengguna menyebut "struk.png", di disk namanya berawalan UUID."""
        assert resolve_image_path("struk.png").name == "abc123__struk.png"

    def test_unggahan_terbaru_yang_dipakai(self, gambar, tmp_path):
        import os, time

        baru = tmp_path / "def456__struk.png"
        baru.write_bytes(b"\x89PNG\r\n\x1a\n")
        os.utime(baru, (time.time() + 10, time.time() + 10))
        assert resolve_image_path("struk.png").name == "def456__struk.png"

    def test_path_traversal_tidak_bisa_keluar_folder(self, gambar):
        with pytest.raises(FileNotFoundError):
            resolve_image_path("../../etc/passwd")

    def test_berkas_tidak_ada_memberi_galat_jelas(self, gambar):
        with pytest.raises(FileNotFoundError, match="tidak ditemukan"):
            resolve_image_path("entah.png")

    def test_ekstensi_bukan_gambar_ditolak(self, gambar, tmp_path):
        (tmp_path / "xyz789__catatan.txt").write_text("halo")
        with pytest.raises(ValueError, match="bukan gambar"):
            resolve_image_path("catatan.txt")


class OcrPalsu:
    """Pengganti PaddleOCR yang mengembalikan hasil yang sudah ditentukan."""

    def __init__(self, teks, skor):
        self._hasil = [{"rec_texts": teks, "rec_scores": skor}]

    def predict(self, _path):
        return self._hasil


class TestPenyaringanKeyakinan:
    def _pasang(self, monkeypatch, teks, skor):
        monkeypatch.setattr(ocr_tool, "_muat_ocr", lambda: OcrPalsu(teks, skor))

    def test_baris_berkeyakinan_rendah_dibuang(self, monkeypatch, tmp_path):
        """Angka yang salah baca lebih berbahaya daripada baris yang hilang."""
        self._pasang(monkeypatch, ["TOTAL 366300", "3bb#@~"], [0.99, 0.12])
        baris, keyakinan = baca_teks(tmp_path / "x.png")
        assert baris == ["TOTAL 366300"]
        assert keyakinan == pytest.approx(0.99)

    def test_keyakinan_yang_dilaporkan_adalah_yang_terendah(self, monkeypatch, tmp_path):
        self._pasang(monkeypatch, ["A", "B", "C"], [0.99, 0.72, 0.85])
        _, keyakinan = baca_teks(tmp_path / "x.png")
        assert keyakinan == pytest.approx(0.72)

    def test_baris_kosong_tidak_ikut(self, monkeypatch, tmp_path):
        self._pasang(monkeypatch, ["TOTAL", "   ", ""], [0.99, 0.99, 0.99])
        baris, _ = baca_teks(tmp_path / "x.png")
        assert baris == ["TOTAL"]

    def test_semua_meragukan_menghasilkan_kosong(self, monkeypatch, tmp_path):
        self._pasang(monkeypatch, ["???", "###"], [0.2, 0.1])
        assert baca_teks(tmp_path / "x.png") == ([], 0.0)

    def test_tepat_di_ambang_tetap_dipakai(self, monkeypatch, tmp_path):
        self._pasang(monkeypatch, ["batas"], [AMBANG_KEYAKINAN])
        baris, _ = baca_teks(tmp_path / "x.png")
        assert baris == ["batas"]

    def test_hasil_kosong_dari_paddle_aman(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ocr_tool, "_muat_ocr", lambda: OcrPalsu([], []))
        assert baca_teks(tmp_path / "x.png") == ([], 0.0)


def _poly(x1, y1, x2, y2):
    """Poligon empat titik seperti yang dikembalikan PaddleOCR."""
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


class TestSusunBaris:
    """PaddleOCR mengembalikan tiap kotak teks terpisah.

    Tanpa perangkaian ulang, "TOTAL" dan "366300" yang bersebelahan pada
    struk datang sebagai dua baris dan kaitannya hilang — pada pengujian
    nyata hal itu membuat model menjawab nilai "Tunai", bukan "TOTAL".
    """

    def test_potongan_sebaris_digabung_kiri_ke_kanan(self):
        teks = ["366300", "TOTAL"]
        polys = [_poly(85, 358, 150, 373), _poly(24, 358, 70, 373)]
        assert susun_baris(teks, polys) == ["TOTAL  366300"]

    def test_baris_berbeda_tetap_terpisah(self):
        teks = ["TOTAL", "366300", "Tunai", "400000"]
        polys = [_poly(24, 358, 70, 373), _poly(85, 358, 150, 373),
                 _poly(23, 424, 70, 442), _poly(82, 425, 150, 440)]
        assert susun_baris(teks, polys) == ["TOTAL  366300", "Tunai  400000"]

    def test_selisih_vertikal_kecil_masih_dianggap_sebaris(self):
        """Kotak teks pada baris yang sama jarang sejajar sempurna."""
        teks = ["Tinta Printer", "1x 185000"]
        polys = [_poly(26, 187, 90, 202), _poly(93, 188, 160, 200)]
        assert susun_baris(teks, polys) == ["Tinta Printer  1x 185000"]

    def test_kotak_sejajar_sumbu_juga_diterima(self):
        """PaddleOCR bisa mengembalikan rec_boxes berbentuk [x1, y1, x2, y2]."""
        kotak = [[24, 358, 70, 373], [85, 358, 150, 373]]
        assert susun_baris(["TOTAL", "366300"], kotak) == ["TOTAL  366300"]

    def test_tanpa_koordinat_urutan_asli_dipertahankan(self):
        assert susun_baris(["A", "B"], []) == ["A", "B"]

    def test_jumlah_koordinat_tidak_cocok_tidak_membuat_gagal(self):
        assert susun_baris(["A", "B"], [_poly(0, 0, 10, 10)]) == ["A", "B"]

    def test_teks_kosong_diabaikan(self):
        teks = ["TOTAL", "   ", "366300"]
        polys = [_poly(24, 358, 70, 373), _poly(200, 358, 210, 373),
                 _poly(85, 358, 150, 373)]
        assert susun_baris(teks, polys) == ["TOTAL  366300"]

    def test_urutan_vertikal_dipulihkan(self):
        """Masukan yang acak urutannya tetap tersusun dari atas ke bawah."""
        teks = ["Kembali", "TOTAL", "Tunai"]
        polys = [_poly(24, 460, 90, 475), _poly(24, 358, 70, 373),
                 _poly(23, 424, 70, 442)]
        assert susun_baris(teks, polys) == ["TOTAL", "Tunai", "Kembali"]


class TestMedanNumpy:
    """PaddleOCR mengembalikan sebagian medan sebagai `numpy.ndarray`.

    `OcrPalsu` di atas hanya memakai list, dan justru itulah sebabnya B-30
    lolos dari seluruh test sampai ditemukan pengguna: pada array, `a or b`
    melempar ValueError alih-alih menghasilkan False. Kelas ini memakai
    array sungguhan supaya jalur itu ikut teruji.
    """

    class OcrNumpy:
        def __init__(self, hasil):
            self._hasil = [hasil]

        def predict(self, _path):
            return self._hasil

    def _pasang(self, monkeypatch, hasil):
        monkeypatch.setattr(ocr_tool, "_muat_ocr", lambda: self.OcrNumpy(hasil))

    def test_gambar_tanpa_teks_tidak_menggagalkan_pembacaan(
        self, monkeypatch, tmp_path
    ):
        """B-30: gambar tanpa tulisan sama sekali (mis. foto atau gambar).

        Deteksi nol adalah hasil yang sah, bukan kegagalan. Sebelum
        perbaikan, `rec_boxes` berupa array kosong membuat seluruh
        pembacaan melempar ValueError, dan pengguna menerima "gagal
        membaca" padahal jawabannya semestinya "tidak ada teks".
        """
        import numpy as np

        self._pasang(monkeypatch, {
            "rec_texts": [],
            "rec_scores": [],
            "rec_polys": [],
            "rec_boxes": np.empty((0,)),
        })
        assert baca_teks(tmp_path / "mobil.jpeg") == ([], 0.0)

    def test_rec_boxes_berupa_array_tetap_dipakai(self, monkeypatch, tmp_path):
        """Bila `rec_polys` kosong, koordinat diambil dari `rec_boxes`."""
        import numpy as np

        self._pasang(monkeypatch, {
            "rec_texts": ["TOTAL", "366300"],
            "rec_scores": [0.99, 0.98],
            "rec_polys": [],
            "rec_boxes": np.array([[10, 100, 60, 120], [200, 100, 260, 120]]),
        })
        baris, _ = baca_teks(tmp_path / "struk.png")
        assert baris == ["TOTAL  366300"]

    def test_rec_polys_berupa_array_tetap_dipakai(self, monkeypatch, tmp_path):
        import numpy as np

        self._pasang(monkeypatch, {
            "rec_texts": ["A", "B"],
            "rec_scores": [0.9, 0.9],
            "rec_polys": np.array([_poly(10, 10, 40, 30), _poly(10, 90, 40, 110)]),
        })
        baris, _ = baca_teks(tmp_path / "x.png")
        assert baris == ["A", "B"]
