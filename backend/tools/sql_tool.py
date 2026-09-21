"""Tool 3 — SQL Query (PRD §8 dan §18).

Query ditulis oleh LLM, jadi isinya tidak boleh dipercaya. Pertahanannya
berlapis, dan lapisan terpenting ada di luar kode ini:

1. **PostgreSQL** — koneksi memakai user `rag_readonly` yang hanya punya
   SELECT, dengan `default_transaction_read_only = on` dan
   `statement_timeout = 10s` (keputusan D-05). Seandainya seluruh validasi
   di bawah ditembus, database tetap menolak perubahan data.
2. **Validasi di modul ini** — menolak lebih awal dengan pesan yang bisa
   dipahami model, sehingga ia memperbaiki query-nya sendiri, bukan
   menabrak galat database yang membingungkan.
3. **Batas jumlah baris** — LIMIT dipasang paksa agar satu query tidak
   menarik seluruh isi tabel ke dalam konteks LLM.
"""

from __future__ import annotations

import logging
import re

from langchain_core.tools import tool
from sqlalchemy import text

from backend.config import settings
from backend.database import sql_agent_engine
from backend.tools import ToolInvocation, record

logger = logging.getLogger(__name__)


class SQLValidationError(ValueError):
    """Query ditolak sebelum dijalankan."""


# Kata kunci yang mengubah data atau struktur. Dicocokkan sebagai kata utuh
# agar kolom bernama "updated_at" tidak ikut tertangkap oleh "UPDATE".
KATA_TERLARANG = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "COPY", "VACUUM", "REINDEX", "CALL", "DO",
    "EXECUTE", "PREPARE", "LISTEN", "NOTIFY", "SET", "RESET",
)

# Fungsi yang bisa membaca berkas atau menjalankan perintah di server.
FUNGSI_TERLARANG = ("pg_read_file", "pg_read_binary_file", "pg_ls_dir", "lo_import", "lo_export")

POLA_TABEL = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_.\"]*)", re.IGNORECASE)
# Nama sementara yang didefinisikan CTE: WITH x AS (...), ", y AS (...)".
POLA_CTE = re.compile(r"(?:\bWITH\s+(?:RECURSIVE\s+)?|,\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s+AS\s*\(", re.IGNORECASE)
POLA_LIMIT = re.compile(r"\bLIMIT\s+(\d+)", re.IGNORECASE)
POLA_KOMENTAR = re.compile(r"--|/\*|\*/")


def validate_sql(query: str) -> str:
    """Periksa query dan kembalikan versi yang aman dijalankan.

    Raises:
        SQLValidationError: dengan pesan yang menjelaskan sebabnya, supaya
            model dapat memperbaiki sendiri query berikutnya.
    """
    bersih = query.strip().rstrip(";").strip()

    if not bersih:
        raise SQLValidationError("Query kosong.")

    # Komentar dilarang karena kerap dipakai menyembunyikan perintah kedua.
    if POLA_KOMENTAR.search(bersih):
        raise SQLValidationError("Query tidak boleh memuat komentar SQL.")

    if ";" in bersih:
        raise SQLValidationError(
            "Hanya satu perintah SELECT yang boleh dijalankan sekaligus."
        )

    if not re.match(r"^\s*(SELECT|WITH)\b", bersih, re.IGNORECASE):
        raise SQLValidationError("Hanya perintah SELECT yang diizinkan.")

    huruf_besar = bersih.upper()
    for kata in KATA_TERLARANG:
        if re.search(rf"\b{kata}\b", huruf_besar):
            raise SQLValidationError(f"Perintah '{kata}' tidak diizinkan.")

    for fungsi in FUNGSI_TERLARANG:
        if fungsi.lower() in bersih.lower():
            raise SQLValidationError(f"Fungsi '{fungsi}' tidak diizinkan.")

    # Nama yang didefinisikan CTE ikut dianggap sah: ia hanya hidup di dalam
    # query itu sendiri, sedangkan tabel nyata yang dibaca CTE tetap diperiksa
    # lewat klausa FROM di dalamnya.
    diizinkan = {t.lower() for t in settings.sql_agent_allowed_tables}
    diizinkan |= {nama.lower() for nama in POLA_CTE.findall(bersih)}

    for tabel in POLA_TABEL.findall(bersih):
        nama = tabel.strip('"').split(".")[-1].lower()
        if nama not in diizinkan:
            raise SQLValidationError(
                f"Tabel '{nama}' tidak ada dalam daftar yang diizinkan. "
                f"Tabel yang boleh dipakai: {', '.join(sorted(diizinkan))}."
            )

    # LIMIT dipasang paksa. Bila model sudah menulisnya lebih besar dari
    # batas, nilainya diturunkan.
    maks = settings.sql_agent_max_rows
    cocok = POLA_LIMIT.search(bersih)
    if cocok is None:
        bersih = f"{bersih} LIMIT {maks}"
    elif int(cocok.group(1)) > maks:
        bersih = POLA_LIMIT.sub(f"LIMIT {maks}", bersih, count=1)

    return bersih


def _format_hasil(kolom: list[str], baris: list[tuple]) -> str:
    """Susun hasil query menjadi teks yang mudah dibaca model."""
    if not baris:
        return "Query berhasil, tetapi tidak ada baris yang cocok."

    garis = [" | ".join(kolom), "-" * 40]
    garis += [" | ".join("" if n is None else str(n) for n in b) for b in baris]
    garis.append(f"({len(baris)} baris)")
    return "\n".join(garis)


@tool("SQL_Query")
def sql_query(query: str) -> str:
    """Jalankan satu perintah SELECT PostgreSQL untuk mengambil data.

    Pakai untuk hitungan, agregasi, atau daftar baris dari tabel berikut:

      pegawai(id, nama, nip, bagian, jabatan, tanggal_masuk)
      pengajuan_cuti(id, pegawai_id, jenis, tanggal_mulai, tanggal_selesai,
                     jumlah_hari, status, dibuat_pada)
      chat_history(id, session_id, role, message, created_at)
      documents(id, filename, content, metadata, created_at)

    Catatan: satu baris `documents` adalah satu potongan, bukan satu berkas.
    Hanya SELECT. Tanpa titik koma dan tanpa komentar.

    Args:
        query: Satu perintah SELECT PostgreSQL yang lengkap.
    """
    try:
        aman = validate_sql(query)
    except SQLValidationError as exc:
        record(ToolInvocation("SQL_Query", ok=False, detail=str(exc)))
        logger.warning("SQL ditolak: %s | query=%r", exc, query)
        return f"Query ditolak: {exc} Perbaiki lalu coba lagi."

    try:
        with sql_agent_engine.connect() as conn:
            hasil = conn.execute(text(aman))
            kolom = list(hasil.keys())
            baris = hasil.fetchall()
    except Exception as exc:
        record(ToolInvocation("SQL_Query", ok=False, detail=str(exc)))
        logger.warning("SQL gagal: %s", exc)
        # Detail galat database tidak diteruskan mentah-mentah agar struktur
        # internal tidak bocor lewat jawaban.
        return "Query gagal dijalankan. Periksa nama kolom dan tabelnya."

    record(ToolInvocation("SQL_Query", ok=True, detail=aman))
    logger.info("SQL_Query dijalankan: %s -> %d baris", aman, len(baris))
    return _format_hasil(kolom, [tuple(b) for b in baris])
