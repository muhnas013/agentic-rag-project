"""Uji bagian pipeline dokumen yang tidak memerlukan database."""

import pytest

from backend.config import settings
from backend.services import document_service as ds
from backend.services.embedding_service import HashStubEmbedding

PDF_HEAD = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
PNG_HEAD = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class TestValidateUpload:
    def test_menerima_teks_biasa(self):
        assert ds.validate_upload("catatan.txt", b"halo dunia") == ".txt"

    def test_menolak_ekstensi_di_luar_allowlist(self):
        with pytest.raises(ds.UploadValidationError, match="tidak diizinkan"):
            ds.validate_upload("skrip.exe", b"MZ\x90\x00")

    def test_menolak_berkas_kosong(self):
        with pytest.raises(ds.UploadValidationError, match="kosong"):
            ds.validate_upload("kosong.txt", b"")

    def test_menolak_ekstensi_yang_dipalsukan(self):
        """Berkas PNG yang dinamai .pdf harus tertangkap lewat signature."""
        with pytest.raises(ds.UploadValidationError):
            ds.validate_upload("gambar.pdf", PNG_HEAD)

    def test_menerima_pdf_yang_sah(self):
        assert ds.validate_upload("dokumen.pdf", PDF_HEAD) == ".pdf"

    def test_menolak_riff_yang_bukan_webp(self):
        wav = b"RIFF\x24\x00\x00\x00WAVEfmt "
        with pytest.raises(ds.UploadValidationError, match="bukan gambar WEBP"):
            ds.validate_upload("suara.webp", wav)

    def test_ekstensi_huruf_besar_tetap_diterima(self):
        assert ds.validate_upload("LAPORAN.PDF", PDF_HEAD) == ".pdf"


class TestCleanAndChunk:
    def test_membuang_spasi_dan_baris_berlebih(self):
        assert ds.clean_text("halo   dunia\n\n\n\nlagi") == "halo dunia\n\nlagi"

    def test_potongan_tidak_melebihi_chunk_size(self):
        chunks = ds.chunk_text("kalimat panjang. " * 400)
        assert len(chunks) > 1
        assert all(len(chunk) <= settings.chunk_size for chunk in chunks)

    def test_teks_pendek_menjadi_satu_potongan(self):
        assert ds.chunk_text("cuma satu baris") == ["cuma satu baris"]


class TestHashStubEmbedding:
    def test_dimensi_sesuai_konfigurasi(self):
        vector = HashStubEmbedding()._embed_sync("uji dimensi")
        assert len(vector) == settings.embedding_dim

    def test_deterministik(self):
        backend = HashStubEmbedding()
        assert backend._embed_sync("teks sama") == backend._embed_sync("teks sama")

    def test_vektor_dinormalisasi(self):
        vector = HashStubEmbedding()._embed_sync("panjang vektor harus satu")
        assert abs(sum(value * value for value in vector) - 1.0) < 1e-9

    def test_teks_mirip_lebih_dekat_daripada_teks_berbeda(self):
        backend = HashStubEmbedding()
        acuan = backend._embed_sync("masa retensi dokumen kepegawaian")
        mirip = backend._embed_sync("berapa lama masa retensi dokumen")
        beda = backend._embed_sync("resep rendang daging sapi")

        def cosine(a, b):
            return sum(x * y for x, y in zip(a, b))

        assert cosine(acuan, mirip) > cosine(acuan, beda)


def _chunk(score: float) -> ds.RetrievedChunk:
    return ds.RetrievedChunk(
        id=int(score * 1000), filename="uji.txt", content="isi", score=score, metadata={}
    )


class TestFilterRelevant:
    def test_membuang_potongan_berskor_nol(self):
        chunks = [_chunk(0.8), _chunk(0.5), _chunk(0.0)]
        assert [c.score for c in ds.filter_relevant(chunks, 0.5)] == [0.8, 0.5]

    def test_membuang_yang_jauh_di_bawah_terbaik(self):
        chunks = [_chunk(0.8), _chunk(0.1)]
        assert [c.score for c in ds.filter_relevant(chunks, 0.5)] == [0.8]

    def test_potongan_terbaik_selalu_dipertahankan(self):
        """Penyaringan tidak boleh mengosongkan konteks, sekecil apa pun skornya."""
        assert len(ds.filter_relevant([_chunk(0.01)], 0.5)) == 1

    def test_rasio_nol_mematikan_penyaringan(self):
        chunks = [_chunk(0.8), _chunk(0.0)]
        assert len(ds.filter_relevant(chunks, 0.0)) == 2

    def test_daftar_kosong_aman(self):
        assert ds.filter_relevant([], 0.5) == []

    def test_skor_setara_tetap_dipakai_semua(self):
        """Pertanyaan yang jawabannya tersebar di beberapa dokumen."""
        chunks = [_chunk(0.6), _chunk(0.55), _chunk(0.5)]
        assert len(ds.filter_relevant(chunks, 0.5)) == 3


class TestTataLetakPDF:
    """Spasi berderet pada PDF bermakna: itulah yang menjaga kolom sejajar.

    `clean_text` semula meratakannya menjadi satu spasi, sehingga kaitan
    antara sel tabel dan barisnya putus sebelum sampai ke model. Pada
    pengujian, pertanyaan "siapa yang menyetujui pengadaan 150 juta"
    karena itu dijawab dari dokumen yang salah.
    """

    BARIS_TABEL = "Di atas Rp 10.000.000 sampai Rp        Sekretaris Dinas        5 hari kerja"

    def test_kolom_tetap_terpisah_pada_mode_tata_letak(self):
        hasil = ds.clean_text(self.BARIS_TABEL, pertahankan_tata_letak=True)
        assert "Rp        Sekretaris" in hasil

    def test_mode_biasa_tetap_meratakan(self):
        """Teks biasa tidak punya kolom, jadi spasi berlebih hanya memboroskan."""
        hasil = ds.clean_text(self.BARIS_TABEL, pertahankan_tata_letak=False)
        assert "Rp Sekretaris" in hasil

    def test_deret_spasi_sangat_panjang_dipotong(self):
        """Deret panjang tidak menambah kejelasan, hanya memakan jatah potongan."""
        hasil = ds.clean_text("A" + " " * 60 + "B", pertahankan_tata_letak=True)
        assert " " * ds.MAKS_SPASI_BERDERET + "B" in hasil
        assert " " * (ds.MAKS_SPASI_BERDERET + 1) not in hasil

    def test_spasi_di_ujung_baris_tetap_dibuang(self):
        hasil = ds.clean_text("kolom     \nberikutnya", pertahankan_tata_letak=True)
        assert "kolom\nberikutnya" == hasil

    def test_baris_kosong_beruntun_tetap_dipadatkan(self):
        hasil = ds.clean_text("A\n\n\n\n\nB", pertahankan_tata_letak=True)
        assert hasil == "A\n\nB"
