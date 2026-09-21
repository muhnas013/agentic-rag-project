# Keputusan Teknologi

Dokumen ini mencatat teknologi yang dipakai beserta alasannya. Semua pilihan
mengikuti `prd.md` §4; deviasi dari PRD ditandai eksplisit dan diberi alasan.

## Lingkungan mesin pengembangan

Hasil pemeriksaan (21 Sep 2026):

| Komponen | Terpasang            | Catatan                                   |
|----------|----------------------|-------------------------------------------|
| CPU      | 24 core              | Di atas rekomendasi PRD (8 core)          |
| RAM      | 15 GB                | Di bawah rekomendasi 32 GB, cukup untuk MVP |
| GPU      | RTX 4060 Laptop 8 GB | Memenuhi rekomendasi VRAM 8 GB            |
| Docker   | 29.7.2 + Compose 5.4 | Tersedia                                  |
| Node     | 26.7.0 / npm 11.19   | Untuk frontend Vite                       |
| psql     | 18.4 (client)        | Server dijalankan via Docker              |
| Python   | **3.14.7 saja**      | Lihat keputusan D-01                      |
| Ollama   | **belum terpasang**  | Dipasang pada Fase 3                      |

## Stack sesuai PRD

| Lapisan        | Pilihan                          | Referensi PRD |
|----------------|----------------------------------|---------------|
| Frontend       | ViteJS + React + TailwindCSS     | §4.1          |
| HTTP client    | Axios                            | §4.1          |
| API framework  | FastAPI + Uvicorn                | §4.2          |
| Agent          | LangChain                        | §4.2          |
| Local LLM      | Ollama                           | §4.2          |
| Embedding      | nomic-embed-text (768 dim)       | §4.2, §7.2    |
| OCR            | PaddleOCR                        | §4.2          |
| ORM            | SQLAlchemy                       | §4.2          |
| Database       | PostgreSQL + pgvector            | §4.3          |

## Keputusan tambahan

### D-01 — Backend dijalankan di Docker dengan Python 3.12

**Masalah.** Host hanya menyediakan Python 3.14.7. PRD §4.2 mensyaratkan
Python 3.10+, tetapi `paddlepaddle` (dependency PaddleOCR) belum merilis wheel
untuk 3.14, sehingga instalasi di host akan gagal pada Fase 5.

**Keputusan.** Backend berjalan di container `python:3.12-slim`, sejalan dengan
anjuran "Docker: Recommended" pada PRD §5 dan arsitektur Docker pada PRD §21.
Host tidak perlu dipasangi Python tambahan.

**Konsekuensi.** Perintah pengembangan dijalankan lewat `docker compose`.
Kode sumber di-mount sebagai volume agar hot-reload Uvicorn tetap berfungsi.

### D-02 — Model LLM: `llama3.1:8b`

PRD §12 mencontohkan `llama3`. Dipilih `llama3.1:8b` (kuantisasi Q4, ±4,7 GB)
karena muat di VRAM 8 GB dan merupakan penerus langsung dari contoh di PRD.
Diganti lewat `OLLAMA_LLM_MODEL` di `.env` tanpa perubahan kode.

### D-03 — Ollama berjalan di host, bukan container

PRD §22 menyatakan hal ini opsional. Ollama di host mendapat akses GPU NVIDIA
secara langsung tanpa konfigurasi container toolkit. Backend mengaksesnya
melalui `host.docker.internal`.

### D-04 — Driver PostgreSQL: `psycopg` (v3)

PRD tidak menyebut driver spesifik. `psycopg` v3 dipilih karena aktif
dikembangkan dan didukung penuh SQLAlchemy 2.x, berbeda dengan `psycopg2`
yang berstatus maintenance.

### D-05 — Dua koneksi database terpisah

Sesuai PRD §18, SQL Tool memakai koneksi user read-only
(`SQL_AGENT_DATABASE_URL`) yang berbeda dari koneksi aplikasi
(`DATABASE_URL`). Pembatasan ini ditegakkan pada level PostgreSQL grant,
bukan hanya validasi di kode.
