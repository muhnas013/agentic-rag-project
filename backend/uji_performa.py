"""Pengukuran performa dasar (checklist Fase 7).

Mengukur latensi tiap bagian sistem secara terpisah, bukan hanya waktu
jawaban akhir. Tanpa pemisahan itu, satu angka besar tidak memberi tahu
apa pun: 6 detik bisa berarti embedding lambat, pencarian lambat, atau
model lambat — dan tindakannya berbeda-beda.

Jalankan:
    docker compose exec -w /app backend python -m backend.uji_performa
"""

from __future__ import annotations

import asyncio
import statistics
import time
from pathlib import Path

from backend.agent import run_agent
from backend.config import settings
from backend.database import SessionLocal, check_database_connection
from backend.services.document_service import search_similar_chunks
from backend.services.embedding_service import embed_query


async def ukur(nama: str, fn, ulang: int = 5) -> dict:
    """Jalankan `fn` beberapa kali, laporkan sebaran waktunya."""
    waktu = []
    for _ in range(ulang):
        mulai = time.perf_counter()
        hasil = fn()
        if asyncio.iscoroutine(hasil):
            await hasil
        waktu.append(time.perf_counter() - mulai)
    return {
        "nama": nama,
        "min": min(waktu),
        "median": statistics.median(waktu),
        "maks": max(waktu),
    }


async def main() -> None:
    db = SessionLocal()
    baris = []

    try:
        baris.append(await ukur("Koneksi database", check_database_connection, 10))
        baris.append(await ukur("Embedding satu pertanyaan",
                                lambda: embed_query("berapa lama masa retensi dokumen"), 5))
        baris.append(await ukur("Pencarian pgvector (top_k=4)",
                                lambda: search_similar_chunks(db, "masa retensi dokumen"), 5))

        # Tiap tool diukur terpisah: beban kerjanya jauh berbeda.
        baris.append(await ukur("Agent — tanpa tool (sapaan)",
                                lambda: run_agent("Halo, selamat pagi"), 3))
        baris.append(await ukur("Agent — RAG_Search",
                                lambda: run_agent(
                                    "Menurut dokumen, berapa lama masa retensi dokumen keuangan?"), 3))
        baris.append(await ukur("Agent — SQL_Query",
                                lambda: run_agent("Ada berapa pegawai di bagian TIK?"), 3))

        gambar = sorted(Path(settings.upload_dir).glob("*struk-uji.png"))
        if gambar:
            from backend.tools.ocr_tool import baca_teks

            # Pemanggilan pertama memuat model OCR ke memori; diukur terpisah
            # supaya tidak mengaburkan biaya pembacaan yang sebenarnya.
            mulai = time.perf_counter()
            baca_teks(gambar[-1])
            pemanasan = time.perf_counter() - mulai
            baris.append(await ukur("OCR satu gambar (model sudah dimuat)",
                                    lambda: baca_teks(gambar[-1]), 3))
        else:
            pemanasan = None
    finally:
        db.close()

    lebar = max(len(b["nama"]) for b in baris)
    print(f"\n{'Bagian':<{lebar}}  {'min':>8}  {'median':>8}  {'maks':>8}")
    print("-" * (lebar + 30))
    for b in baris:
        print(f"{b['nama']:<{lebar}}  {b['min']*1000:>7.0f}ms  "
              f"{b['median']*1000:>7.0f}ms  {b['maks']*1000:>7.0f}ms")

    if pemanasan:
        print(f"\nPemuatan model OCR pertama kali: {pemanasan:.1f}s "
              "(sekali per proses, bukan per permintaan)")

    print(f"\nModel LLM      : {settings.llm_model_name}")
    print(f"Model embedding: {settings.embedding_model_name} "
          f"({settings.embedding_dim} dimensi)")


if __name__ == "__main__":
    asyncio.run(main())
