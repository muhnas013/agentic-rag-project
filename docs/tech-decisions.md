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

### D-02 — Model LLM: `qwen2.5:7b-instruct-q4_K_M`

PRD §12 mencontohkan `llama3`. Dipilih Qwen2.5 7B Instruct kuantisasi Q4_K_M
(unduh 4,7 GB, konteks 32K) setelah membandingkan empat kandidat.

**Alasan.** Agent pada PRD §14 harus memilih sendiri di antara tiga tool, jadi
keandalan *tool calling* lebih menentukan daripada ukuran model. Qwen2.5 7B
menghasilkan JSON tool call yang konsisten dan menguasai bahasa Indonesia
lebih baik daripada Llama 3.1 8B. Satu pertanyaan memicu sekitar tiga panggilan
LLM (pilih tool → olah hasil tool → susun jawaban), sehingga latensi berlipat
dan model yang lebih ramping terasa jauh lebih enak dipakai.

**Anggaran VRAM** dari 7,8 GB yang bebas di RTX 4060:

| Komponen              | VRAM   |
|-----------------------|--------|
| Bobot LLM             | 4,7 GB |
| KV cache (8K konteks) | 0,5 GB |
| `nomic-embed-text`    | 0,3 GB |
| **Total**             | **5,5 GB** |
| Sisa                  | 2,3 GB |

Sisa 2,3 GB mencegah layer melimpah ke CPU saat konteks membengkak.

**Alternatif yang ditolak.** `qwen3:8b` bernalar lebih baik tetapi menyisakan
hanya 0,7 GB. `llama3.1:8b` lebih lemah pada bahasa Indonesia. `qwen3:4b`
terlalu sering salah memilih tool pada pertanyaan ambigu.

**Konteks dibatasi 8K** lewat `OLLAMA_NUM_CTX`, bukan 32K bawaan model, agar
KV cache tetap kecil. Nilainya cukup untuk system prompt, definisi tool, empat
potongan dokumen, dan riwayat percakapan.

### D-02b — Embedding: `nomic-embed-text` (768 dimensi)

Sesuai default PRD §12, sehingga kolom `embedding VECTOR(768)` pada PRD §7.2
dipakai apa adanya.

**Risiko yang diterima.** Model ini berorientasi bahasa Inggris. Pada tolok
ukur retrieval, `bge-m3` mencapai 72% berbanding 57% milik `nomic-embed-text`,
sehingga pada dokumen berbahasa Indonesia potongan yang relevan lebih sering
tidak terambil. Risiko ini diambil secara sadar demi menghemat 0,9 GB VRAM dan
tetap setia pada PRD.

**Mitigasi.** Dimensi vektor tidak ditulis mati di kode, melainkan dibaca dari
`EMBEDDING_DIM` di `.env`. Bila pengujian retrieval pada Fase 7 mengecewakan,
pindah ke `bge-m3` cukup dengan mengubah dua variabel `.env`
(`OLLAMA_EMBEDDING_MODEL=bge-m3`, `EMBEDDING_DIM=1024`), menjalankan migrasi
kolom, lalu melakukan embedding ulang atas dokumen — tanpa mengubah kode.

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
