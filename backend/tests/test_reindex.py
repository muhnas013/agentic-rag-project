"""Uji pendataan dokumen pada skrip embedding ulang.

Bagian yang memanggil model sengaja tidak diuji di sini; yang penting adalah
skrip ini benar mengenali dokumen mana yang masih memakai model lama, karena
itulah satu-satunya tanda yang tersedia — selisih model tidak menimbulkan
galat apa pun saat pencarian.
"""

from backend.models import Document
from backend.reindex import _daftar_dokumen


class SessionPalsu:
    """Session minimal yang mengembalikan baris yang sudah disiapkan."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, _statement):
        return self

    def all(self):
        return self._rows


def test_potongan_dihitung_per_berkas():
    rows = [
        ("a.txt", {"embedding_model": "nomic-embed-text", "source_path": "/x/a.txt"}),
        ("a.txt", {"embedding_model": "nomic-embed-text", "source_path": "/x/a.txt"}),
        ("b.pdf", {"embedding_model": "hash_stub", "source_path": "/x/b.pdf"}),
    ]
    hasil = _daftar_dokumen(SessionPalsu(rows))

    assert set(hasil) == {"a.txt", "b.pdf"}
    assert hasil["a.txt"]["potongan"] == 2
    assert hasil["b.pdf"]["potongan"] == 1


def test_model_dan_path_terbaca():
    rows = [("a.txt", {"embedding_model": "hash_stub", "source_path": "/x/a.txt"})]
    hasil = _daftar_dokumen(SessionPalsu(rows))

    assert hasil["a.txt"]["model"] == "hash_stub"
    assert hasil["a.txt"]["source_path"] == "/x/a.txt"


def test_metadata_kosong_tidak_membuat_gagal():
    """Baris lama bisa saja tidak punya metadata sama sekali."""
    hasil = _daftar_dokumen(SessionPalsu([("lama.txt", None)]))

    assert hasil["lama.txt"]["model"] == "?"
    assert hasil["lama.txt"]["source_path"] == ""


def test_kolom_metadata_bernama_metadata_di_database():
    """Atribut Python-nya doc_metadata, nama kolomnya tetap 'metadata' (PRD §7.2)."""
    assert Document.__table__.c.metadata.name == "metadata"
