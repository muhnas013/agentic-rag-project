"""Uji lapisan validasi SQL Tool (PRD §18).

Validasi ini adalah lapisan kedua; lapisan pertama adalah grant PostgreSQL
pada user read-only. Test di sini memastikan query berbahaya ditolak lebih
awal dengan pesan yang bisa dipahami model.
"""

import pytest

from backend.config import settings
from backend.tools.sql_tool import SQLValidationError, validate_sql


class TestQueryYangDiterima:
    def test_select_sederhana_dipasangi_limit(self):
        hasil = validate_sql("SELECT filename FROM documents")
        assert hasil == f"SELECT filename FROM documents LIMIT {settings.sql_agent_max_rows}"

    def test_titik_koma_di_ujung_dibuang(self):
        assert validate_sql("SELECT id FROM documents;").startswith("SELECT id FROM documents")

    def test_cte_with_diizinkan(self):
        """Nama sementara CTE bukan tabel nyata, jadi tidak perlu di-allowlist."""
        hasil = validate_sql(
            "WITH x AS (SELECT filename FROM documents) SELECT count(*) FROM x"
        )
        assert hasil.startswith("WITH x AS")

    def test_cte_tetap_memeriksa_tabel_nyata_di_dalamnya(self):
        """CTE tidak boleh jadi celah untuk membaca tabel di luar allowlist."""
        with pytest.raises(SQLValidationError, match="tidak ada dalam daftar"):
            validate_sql("WITH x AS (SELECT usename FROM pg_user) SELECT * FROM x")

    def test_limit_wajar_dipertahankan(self):
        assert "LIMIT 5" in validate_sql("SELECT id FROM documents LIMIT 5")

    def test_limit_kelewat_besar_diturunkan(self):
        hasil = validate_sql("SELECT id FROM documents LIMIT 999999")
        assert f"LIMIT {settings.sql_agent_max_rows}" in hasil
        assert "999999" not in hasil

    def test_kolom_mirip_kata_terlarang_tidak_ikut_tertangkap(self):
        """'updated_at' memuat 'UPDATE' — pencocokan harus per kata utuh."""
        assert validate_sql("SELECT created_at FROM chat_history")


class TestQueryYangDitolak:
    @pytest.mark.parametrize(
        "query",
        [
            "DELETE FROM documents",
            "DROP TABLE documents",
            "UPDATE documents SET content = 'x'",
            "INSERT INTO documents (filename) VALUES ('x')",
            "TRUNCATE chat_history",
            "GRANT ALL ON documents TO rag_readonly",
            "ALTER TABLE documents ADD COLUMN x int",
        ],
    )
    def test_perintah_perubahan_data_ditolak(self, query):
        with pytest.raises(SQLValidationError):
            validate_sql(query)

    def test_dua_perintah_sekaligus_ditolak(self):
        with pytest.raises(SQLValidationError, match="satu perintah"):
            validate_sql("SELECT 1 FROM documents; DROP TABLE documents")

    def test_komentar_ditolak(self):
        """Komentar kerap dipakai menyembunyikan perintah kedua."""
        with pytest.raises(SQLValidationError, match="komentar"):
            validate_sql("SELECT id FROM documents -- DROP TABLE documents")

    def test_tabel_di_luar_allowlist_ditolak(self):
        with pytest.raises(SQLValidationError, match="tidak ada dalam daftar"):
            validate_sql("SELECT usename FROM pg_user")

    def test_join_ke_tabel_terlarang_ikut_ditolak(self):
        with pytest.raises(SQLValidationError, match="tidak ada dalam daftar"):
            validate_sql(
                "SELECT d.id FROM documents d JOIN pg_class c ON c.oid = d.id"
            )

    def test_baca_berkas_server_ditolak(self):
        with pytest.raises(SQLValidationError, match="pg_read_file"):
            validate_sql("SELECT pg_read_file('/etc/passwd') FROM documents")

    def test_query_kosong_ditolak(self):
        with pytest.raises(SQLValidationError, match="kosong"):
            validate_sql("   ")

    def test_bukan_select_ditolak(self):
        with pytest.raises(SQLValidationError, match="Hanya perintah SELECT"):
            validate_sql("EXPLAIN ANALYZE SELECT 1 FROM documents")
