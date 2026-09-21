"""Embedding ulang seluruh dokumen yang sudah terindeks.

Wajib dijalankan setiap kali model embedding berganti. Vektor dari dua model
berbeda tidak sebanding, dan kegagalannya menipu: pencarian tetap
mengembalikan hasil, hanya saja hasilnya acak — tidak ada galat, tidak ada
tanda apa pun. Karena itu skrip ini juga menampilkan model mana yang dipakai
tiap dokumen, supaya baris lama ketahuan sebelum menimbulkan kebingungan.

Berkas asli tetap tersimpan di storage/uploads, jadi tidak perlu meminta
pengguna mengunggah ulang apa pun.

Jalankan:
    docker compose exec -w /app backend python -m backend.reindex            # periksa saja
    docker compose exec -w /app backend python -m backend.reindex --jalan    # kerjakan
    docker compose exec -w /app backend python -m backend.reindex --jalan --paksa
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from backend.config import settings
from backend.database import SessionLocal
from backend.models import Document
from backend.services import document_service

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def _daftar_dokumen(db) -> dict[str, dict]:
    """Kumpulkan satu baris wakil untuk tiap nama berkas."""
    rows = db.execute(
        select(Document.filename, Document.doc_metadata).order_by(Document.id)
    ).all()

    dokumen: dict[str, dict] = {}
    for filename, metadata in rows:
        info = dokumen.setdefault(
            filename,
            {"potongan": 0, "model": (metadata or {}).get("embedding_model", "?"),
             "source_path": (metadata or {}).get("source_path", "")},
        )
        info["potongan"] += 1
    return dokumen


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jalan", action="store_true",
        help="benar-benar lakukan embedding ulang (tanpa ini hanya memeriksa)",
    )
    parser.add_argument(
        "--paksa", action="store_true",
        help="olah ulang semua dokumen walau modelnya sudah cocok. Diperlukan "
             "ketika yang berubah bukan model embedding melainkan cara dokumen "
             "diolah — misalnya penandaan prompt injection yang baru ditambahkan, "
             "yang hanya tertulis saat dokumen diolah ulang.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        dokumen = _daftar_dokumen(db)
        if not dokumen:
            print("Belum ada dokumen terindeks.")
            return 0

        model_aktif = settings.embedding_model_name
        print(f"Model embedding aktif : {model_aktif} ({settings.embedding_dim} dimensi)")
        print(f"Dokumen terindeks     : {len(dokumen)}\n")

        perlu: list[tuple[str, dict]] = []
        hilang: list[str] = []

        for nama, info in sorted(dokumen.items()):
            berkas = Path(info["source_path"]) if info["source_path"] else None
            ada = bool(berkas and berkas.exists())
            sama = info["model"] == model_aktif

            if sama:
                tanda = "dipaksa ulang" if args.paksa else "sudah cocok"
            else:
                tanda = f"pakai '{info['model']}'"
            butuh = args.paksa or not sama
            if not ada:
                tanda += "  [BERKAS ASLI HILANG]"
                if butuh:
                    hilang.append(nama)
            elif butuh:
                perlu.append((nama, info))

            print(f"  {nama:<28} {info['potongan']:>3} potongan   {tanda}")

        if hilang:
            print(
                f"\n{len(hilang)} dokumen tidak punya berkas asli lagi, jadi tidak bisa "
                "di-embedding ulang otomatis. Unggah ulang berkasnya lewat POST /upload."
            )

        if not perlu:
            print("\nTidak ada yang perlu dikerjakan.")
            return 0

        print(f"\n{len(perlu)} dokumen perlu diolah ulang.")
        if not args.jalan:
            print("Jalankan lagi dengan --jalan untuk mengerjakannya.")
            return 0

        hasil = Counter()
        for nama, info in perlu:
            berkas = Path(info["source_path"])
            try:
                jumlah = await document_service.ingest_document(
                    db,
                    original_filename=nama,
                    stored_path=berkas,
                    extension=berkas.suffix.lower(),
                )
                print(f"  OK    {nama:<28} -> {jumlah} potongan")
                hasil["ok"] += 1
            except Exception as exc:
                db.rollback()
                print(f"  GAGAL {nama:<28} -> {exc}")
                hasil["gagal"] += 1

        print(f"\nSelesai: {hasil['ok']} berhasil, {hasil['gagal']} gagal.")
        return 1 if hasil["gagal"] else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
