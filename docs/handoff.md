# Catatan Serah-Terima Sesi

Terakhir diperbarui: 21 September 2026

Dokumen ini merangkum posisi pengerjaan agar sesi berikutnya bisa langsung
menyambung tanpa mengulang pembahasan.

## Posisi saat ini

**Fase 1 (Persiapan & Foundation) selesai. Pemilihan model selesai.
Berikutnya: Fase 2 — Backend Core.**

Rincian tiap item ada di `checklist-progres.md` pada section "Log pengerjaan".
Itu sumber kebenaran status, bukan dokumen ini.

## Yang sudah ada di repo

```
praktek-ai-engineer/
├── prd.md                    spesifikasi (tidak diubah)
├── checklist-progres.md      status + log pengerjaan  <- baca ini dulu
├── README.md                 arsitektur, stack, cara jalan
├── .env / .env.example       konfigurasi (.env tidak masuk Git)
├── .gitignore
├── docs/
│   ├── tech-decisions.md     keputusan D-01 s/d D-05 beserta alasan
│   └── handoff.md            dokumen ini
├── backend/{tools,services}/ masih kosong, baru __init__.py
├── frontend/src/{components,services}/  masih kosong
└── storage/{uploads,processed}/
```

Git sudah diinisialisasi di branch `main`. Belum ada remote — repo hanya
ada di laptop ini.

## Keputusan yang sudah diambil

| Kode | Keputusan | Inti alasan |
|------|-----------|-------------|
| D-01 | Backend di Docker `python:3.12-slim` | Host hanya punya Python 3.14, `paddlepaddle` belum punya wheel-nya |
| D-02 | LLM `qwen2.5:7b-instruct-q4_K_M` | Tool calling andal + bahasa Indonesia kuat, sisa VRAM 2,3 GB |
| D-02b | Embedding `nomic-embed-text` (768) | Sesuai default PRD, hemat VRAM — **ada risiko, lihat bawah** |
| D-03 | Ollama di host, bukan container | Akses GPU langsung tanpa container toolkit |
| D-04 | Driver `psycopg` v3 | Aktif dikembangkan, didukung penuh SQLAlchemy 2.x |
| D-05 | Dua koneksi database terpisah | SQL Tool pakai user read-only (PRD §18) |

## Langkah berikutnya — Fase 2: Backend Core

Sesuai `checklist-progres.md`:

1. `docker-compose.yml` — PostgreSQL 16 + pgvector, volume persisten
2. `backend/requirements.txt` + `Dockerfile` (`python:3.12-slim`)
3. `backend/config.py` — baca `.env` lewat pydantic-settings
4. `backend/main.py` — FastAPI, CORS, endpoint `GET /health`
5. `backend/database.py` — engine SQLAlchemy + session
6. `backend/models.py` — tabel `chat_history` dan `documents`
   (`VECTOR(768)`, dimensi dibaca dari `EMBEDDING_DIM`)
7. Aktifkan extension `vector`, uji koneksi
8. Service upload dokumen, proses embedding, endpoint query RAG, uji retrieval

## Yang belum terpasang di mesin

- **Ollama belum ada.** Dipasang pada Fase 3, lalu:
  ```bash
  ollama pull qwen2.5:7b-instruct-q4_K_M   # 4,7 GB
  ollama pull nomic-embed-text             # 274 MB
  ```
- PostgreSQL berjalan lewat Docker, belum dibuat (Fase 2).

## Hal yang perlu diwaspadai

**RAM lebih sempit daripada VRAM.** Total 15 GB tetapi hanya sekitar 6,4 GB
tersedia. Docker (PostgreSQL + backend) dan PaddleOCR di CPU sama-sama
memakannya. Tutup aplikasi berat saat menguji OCR atau saat demo.

**Kualitas retrieval bahasa Indonesia — cek ulang di Fase 7.**
`nomic-embed-text` berorientasi bahasa Inggris (akurasi retrieval 57%
berbanding 72% milik `bge-m3`). Gejalanya menipu: LLM tetap menjawab lancar
walaupun potongan dokumen yang terambil kurang tepat, jadi kesalahan ini tidak
terlihat kecuali sengaja diuji. Bila hasil uji mengecewakan, pindah ke `bge-m3`
tanpa mengubah kode:

```bash
# 1. .env
OLLAMA_EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024
# 2. ollama pull bge-m3
# 3. migrasi kolom: ALTER TABLE documents ALTER COLUMN embedding TYPE VECTOR(1024);
# 4. embedding ulang seluruh dokumen
```

**`.env` tidak ikut Git.** Bila project dipindah ke mesin lain, salin `.env`
secara manual atau buat ulang dari `.env.example`.

## Cara memulai sesi berikutnya

Jalankan `claude` di `/home/nzrl4h/praktek-ai-engineer`, lalu sampaikan
kira-kira: *"lanjutkan Fase 2 Backend Core, baca dulu docs/handoff.md dan
checklist-progres.md"*.
