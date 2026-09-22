"""Uji hybrid search (PRD §25).

Penggabungan peringkat diuji sebagai fungsi murni; jalur teks penuh diuji
terhadap PostgreSQL sungguhan, karena yang menentukan di sana justru
perilaku `tsquery` — dan di situlah bug pertamanya bersembunyi.
"""

import pytest

from backend.config import settings
from backend.services.document_service import (
    RetrievedChunk,
    gabung_rrf,
    search_fulltext,
)


def potongan(id_: int, nama: str = "a.txt", skor: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(id=id_, filename=nama, content=f"isi {id_}", score=skor, metadata={})


class TestGabungRRF:
    def test_muncul_di_kedua_daftar_naik_ke_atas(self):
        """Inti RRF: yang disepakati dua jalur mengalahkan juara satu jalur."""
        a = [potongan(1), potongan(2)]
        b = [potongan(3), potongan(2)]
        hasil = gabung_rrf(a, b, limit=3)
        assert hasil[0].id == 2

    def test_bobot_mengubah_pemenang(self):
        a = [potongan(1)]
        b = [potongan(2)]
        assert gabung_rrf(a, b, bobot=(1, 3), limit=1)[0].id == 2
        assert gabung_rrf(a, b, bobot=(3, 1), limit=1)[0].id == 1

    def test_bobot_nol_mematikan_satu_jalur(self):
        a = [potongan(1), potongan(2)]
        b = [potongan(3)]
        hasil = gabung_rrf(a, b, bobot=(1, 0), limit=3)
        assert [h.id for h in hasil[:2]] == [1, 2]

    def test_tidak_ada_potongan_ganda(self):
        a = [potongan(1), potongan(2)]
        b = [potongan(1), potongan(2)]
        assert len({h.id for h in gabung_rrf(a, b, limit=5)}) == 2

    def test_menghormati_limit(self):
        a = [potongan(i) for i in range(1, 11)]
        assert len(gabung_rrf(a, limit=3)) == 3

    def test_daftar_kosong_aman(self):
        assert gabung_rrf([], [], limit=3) == []

    def test_satu_daftar_kosong_tidak_menghapus_yang_lain(self):
        hasil = gabung_rrf([potongan(1)], [], limit=3)
        assert [h.id for h in hasil] == [1]

    def test_k_besar_meratakan_pengaruh_peringkat(self):
        """k besar memperkecil selisih antar peringkat — perilaku yang dijanjikan."""
        a = [potongan(1), potongan(2)]
        kecil = gabung_rrf(a, k=1, limit=2)
        besar = gabung_rrf(a, k=1000, limit=2)
        assert (kecil[0].score - kecil[1].score) > (besar[0].score - besar[1].score)


class TestPencarianTeksPenuh:
    """Jalur ini sempat mengembalikan kosong untuk setiap pertanyaan.

    Penyebabnya `plainto_tsquery` yang meng-AND semua kata, sehingga
    "berapa lama masa retensi dokumen" menuntut dokumen memuat "berapa"
    dan "lama" juga. Tidak ada galat — fiturnya hanya diam-diam tidak
    berbuat apa-apa. Test di bawah mengunci agar itu tidak terulang.
    """

    @pytest.fixture
    def dokumen(self, client, nama_berkas):
        client.post(
            "/documents",
            json={
                "filename": nama_berkas,
                "content": "Dokumen kepegawaian disimpan selama 10 tahun "
                           "sejak pegawai berhenti bekerja.",
            },
        )
        return nama_berkas

    def _db(self):
        from backend.database import SessionLocal

        return SessionLocal()

    def test_pertanyaan_wajar_tetap_menemukan(self, dokumen):
        """Kata "berapa" dan "lama" tidak ada di dokumen, dan itu tidak apa-apa."""
        db = self._db()
        try:
            hasil = search_fulltext(db, "berapa lama dokumen kepegawaian disimpan", 5)
        finally:
            db.close()
        assert dokumen in [h.filename for h in hasil]

    def test_stemming_bahasa_indonesia_bekerja(self, dokumen):
        """Dokumen memuat "bekerja"; pertanyaan memakai "pekerjaan".

        Konfigurasi `indonesian` PostgreSQL mengakarkan keduanya menjadi
        "kerja", sehingga pencocokan tetap terjadi meski bentuk katanya
        berbeda. Inilah yang membuat jalur teks penuh berguna pada bahasa
        Indonesia, bukan sekadar pencocokan huruf per huruf.
        """
        db = self._db()
        try:
            hasil = search_fulltext(db, "pekerjaan pegawai berhenti", 5)
        finally:
            db.close()
        assert dokumen in [h.filename for h in hasil]

    def test_batas_stemmer_yang_perlu_diingat(self):
        """Stemmer-nya tidak konsisten, dan itu perlu diketahui.

        "bekerja" dan "pekerjaan" sama-sama menjadi "kerja", tetapi
        "kepegawaian" menjadi "gawai" sedangkan "pegawai" menjadi "gawa" —
        dua lexeme berbeda, sehingga keduanya tidak saling mencocokkan.
        Jalur vektor yang menutupi kekurangan ini, dan itulah alasan
        keduanya digabung alih-alih memilih salah satu.
        """
        from sqlalchemy import func, select

        db = self._db()
        try:
            akar = {
                kata: db.execute(
                    select(func.cast(func.to_tsvector("indonesian", kata), __import__("sqlalchemy").Text))
                ).scalar()
                for kata in ("kepegawaian", "pegawai", "bekerja", "pekerjaan")
            }
        finally:
            db.close()

        assert akar["bekerja"] == akar["pekerjaan"], "pasangan ini seharusnya menyatu"
        assert akar["kepegawaian"] != akar["pegawai"], (
            "bila PostgreSQL kelak menyatukan keduanya, catatan di D-16 perlu diperbarui"
        )

    def test_kata_yang_sama_sekali_asing_tidak_dipaksa_cocok(self, dokumen):
        db = self._db()
        try:
            hasil = search_fulltext(db, "resep rendang daging sapi", 5)
        finally:
            db.close()
        assert dokumen not in [h.filename for h in hasil]

    def test_pertanyaan_berisi_tanda_baca_tidak_membuat_galat(self, dokumen):
        """Masukan pengguna tidak boleh masuk ke tsquery mentah."""
        db = self._db()
        try:
            hasil = search_fulltext(db, "dokumen & kepegawaian | ':'", 5)
        finally:
            db.close()
        assert isinstance(hasil, list)


class TestModePencarian:
    def test_ketiga_mode_dapat_dipanggil_lewat_query(self, client, nama_berkas):
        client.post("/documents", json={"filename": nama_berkas, "content": "kebijakan arsip"})
        for mode in ("vector", "fulltext", "hybrid"):
            r = client.post("/query", json={"query": "kebijakan arsip", "mode": mode})
            assert r.status_code == 200, mode

    def test_mode_asing_ditolak(self, client):
        assert client.post("/query", json={"query": "x", "mode": "ajaib"}).status_code == 422

    def test_bawaannya_mengikuti_setelan(self, client, nama_berkas):
        assert settings.rag_hybrid_enabled is True
        client.post("/documents", json={"filename": nama_berkas, "content": "kebijakan arsip"})
        r = client.post("/query", json={"query": "kebijakan arsip"})
        assert r.status_code == 200
