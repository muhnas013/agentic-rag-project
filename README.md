# Agentic RAG — Local AI System

Sistem AI Assistant yang berjalan **sepenuhnya di mesin lokal**, tanpa satu
pun panggilan ke layanan cloud. LLM bertindak sebagai **Agent** yang memilih
sendiri tool sesuai kebutuhan pertanyaan: mencari di dokumen (RAG), membaca
teks dari gambar (OCR), atau mengambil data terstruktur (SQL).

Spesifikasi lengkap: [`prd.md`](./prd.md) · Progres:
[`checklist-progres.md`](./checklist-progres.md)

## Arsitektur

```
Frontend (Vite + React)
        │  REST / JSON + JWT
        ▼
FastAPI  →  Agent Orchestrator (LangChain)
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
     RAG Tool    OCR Tool    SQL Tool
     pgvector    PaddleOCR   PostgreSQL
        └───────────┼───────────┘
                    ▼
            Ollama (Local LLM)
                    ▼
              Final Answer
```

Backend dan database berjalan di Docker; Ollama berjalan di host agar
mendapat akses GPU langsung.

## Stack

| Lapisan   | Teknologi                                      |
|-----------|------------------------------------------------|
| Frontend  | Vite 8, React 19, TailwindCSS 4, Axios         |
| Backend   | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2    |
| Agent     | LangChain 1.x (`create_agent`)                 |
| LLM       | Ollama — `qwen2.5:3b-instruct-q4_K_M`          |
| Embedding | Ollama — `nomic-embed-text` (768 dimensi)      |
| Pencarian | Hybrid — pgvector + PostgreSQL full-text (RRF) |
| OCR       | PaddleOCR 3.x (CPU)                            |
| Database  | PostgreSQL 16 + pgvector                       |
| Auth      | JWT (PyJWT) + bcrypt                           |

Alasan tiap pilihan: [`docs/tech-decisions.md`](./docs/tech-decisions.md)
(D-01 s/d D-15).

## Menjalankan

Panduan lengkap dari mesin kosong: [`docs/menjalankan.md`](./docs/menjalankan.md).

Ringkasnya, bila Ollama dan modelnya sudah terpasang:

```bash
cp .env.example .env            # lalu sesuaikan kredensial
docker compose up -d            # PostgreSQL + backend
curl localhost:8000/health

cd frontend && npm install && npm run dev
```

Buka <http://localhost:5173>, masuk dengan `admin` / `admin`.
Dokumentasi API interaktif: <http://localhost:8000/docs>.

> **Perubahan `.env` butuh `docker compose up -d backend`, bukan `restart`.**
> `restart` memakai ulang environment yang dibekukan saat container dibuat,
> sehingga nilai baru tidak pernah terbaca.

## Endpoint

| Method | Path | Peran minimal | Keterangan |
|--------|------|---------------|------------|
| POST | `/auth/login` | — | Tukar kredensial dengan token JWT |
| GET | `/auth/me` | READ_ONLY | Identitas dan peran pemilik token |
| POST | `/auth/users` | ADMIN | Tambah akun |
| GET | `/auth/users` | ADMIN | Daftar akun |
| GET | `/health` | — | Status database, pgvector, dan model |
| POST | `/upload` | USER | Unggah dokumen atau gambar |
| POST | `/documents` | USER | Tambah dokumen dari teks langsung |
| GET | `/documents` | READ_ONLY | Daftar dokumen terindeks |
| POST | `/query` | READ_ONLY | Pencarian RAG mentah, tanpa LLM; `mode` = `hybrid`/`vector`/`fulltext` |
| POST | `/chat` | READ_ONLY | Jawaban dari Agent |
| GET | `/chat/history` | READ_ONLY | Riwayat percakapan satu sesi |
| GET | `/chat/sessions` | READ_ONLY | Daftar percakapan untuk sidebar |
| DELETE | `/chat/sessions/{id}` | USER | Hapus satu percakapan |

`/query` sengaja dipisah dari `/chat`: bila jawaban keliru, endpoint itu
menunjukkan apakah penyebabnya pada pencarian atau pada model. Parameter
`mode` membandingkan ketiga jalur pencarian — itulah yang membongkar B-24.

## Tool yang dimiliki Agent

| Tool | Kegunaan | Pengamanan |
|------|----------|------------|
| `RAG_Search` | Mencari di dokumen terindeks, **hybrid**: vektor + teks penuh | Potongan bermuatan prompt injection dikarantina |
| `SQL_Query` | `SELECT` ke tabel yang diizinkan | User read-only, allowlist tabel, `LIMIT` paksa, timeout |
| `Image_OCR` | Membaca teks dari gambar | Path dibatasi ke folder unggahan |

## Provider model

Seluruh model berjalan lokal lewat Ollama, sesuai PRD §4.2. Tidak ada jalur
ke API luar: isi dokumen dan pertanyaan tidak pernah meninggalkan mesin ini
(keputusan D-17).

```
LLM_PROVIDER=ollama              # ollama
EMBEDDING_PROVIDER=ollama        # ollama | hash_stub
OLLAMA_LLM_MODEL=qwen2.5:3b-instruct-q4_K_M
```

`hash_stub` adalah embedding hashing tanpa model, khusus pengembangan —
dihitung di dalam proses, bukan layanan luar. Jangan dipakai menilai mutu
retrieval.

> **Berganti model embedding mengharuskan seluruh dokumen diolah ulang.**
> Vektor dua model berbeda tidak sebanding, dan pencarian tetap memberi
> hasil — hanya saja acak, sehingga kesalahannya tidak terlihat. Berkas asli
> tersimpan, jadi tidak perlu mengunggah ulang:
>
> ```bash
> docker compose exec -w /app backend python -m backend.reindex          # periksa
> docker compose exec -w /app backend python -m backend.reindex --jalan  # kerjakan
> ```

## Pengujian

```bash
# 128 test unit + kontrak endpoint (deterministik, memakai tiruan)
docker compose exec -w /app backend python -m pytest backend/tests -q

# matriks uji PRD §17 terhadap sistem yang berjalan
docker compose exec -w /app backend python -m backend.uji_matriks --ulang 3

# performa tiap bagian
docker compose exec -w /app backend python -m backend.uji_performa
```

Bug yang ditemukan sepanjang pengerjaan beserta penyebabnya:
[`docs/bug-log.md`](./docs/bug-log.md).

## Keamanan

Sesuai PRD §18, sistem menerapkan:

- **Authentication** JWT, kata sandi disimpan sebagai hash bcrypt
- **Authorization** tiga peran — ADMIN, USER, READ_ONLY
- **SQL Tool** memakai user database read-only dengan allowlist tabel,
  `LIMIT` paksa, dan timeout — ditegakkan pada level grant PostgreSQL,
  bukan sekadar validasi di kode
- **Validasi upload** ekstensi, MIME type, ukuran, dan signature berkas
- **Mitigasi prompt injection** dua lapis: potongan dokumen bermuatan pola
  pengambilalihan dikarantina saat masuk, dan jawaban yang mengutip system
  prompt diganti penolakan
- `.env` tidak pernah masuk ke Git

`AUTH_ENABLED=false` mematikan autentikasi untuk pengembangan di mesin
sendiri. Itu disengaja, dan ditulis sebagai peringatan di log startup.

## Batasan yang diketahui

Disebut apa adanya karena keduanya mempengaruhi mutu jawaban dan **tidak
menimbulkan galat apa pun** — gejalanya hanya terlihat bila sengaja diuji.

1. **`nomic-embed-text` lemah memisahkan makna dalam bahasa Indonesia.**
   Selisih skor antara dokumen yang benar dan yang salah hanya +0,0018
   sampai +0,0757, dibanding +0,18 ke atas pada bahasa Inggris untuk isi
   yang sama.

   **Sebagian besar dampaknya sudah ditutup hybrid search** (D-16): peringkat
   1 benar naik dari 6/10 menjadi 9/10 pada pertanyaan parafrase. Mengganti
   embedding ke `bge-m3` (D-02b) masih akan membantu, tetapi tidak lagi
   mendesak.

2. **Model 3B tidak selalu tepat memilih tool dan menyusun SQL.**
   Pertanyaan yang menuntut JOIN benar sekitar 1 dari 3 kali, dan alur
   multi-tool dalam satu giliran tidak andal. Naik ke `qwen2.5:7b` (4,68 GB,
   muat di VRAM) hanya mengubah satu baris `.env`.

## Dokumentasi

| Berkas | Isi |
|--------|-----|
| [`prd.md`](./prd.md) | Spesifikasi (tidak diubah) |
| [`checklist-progres.md`](./checklist-progres.md) | Status tiap fase + log pengerjaan |
| [`docs/menjalankan.md`](./docs/menjalankan.md) | Pemasangan dari mesin kosong |
| [`docs/demo.md`](./docs/demo.md) | Skenario peragaan |
| [`docs/tech-decisions.md`](./docs/tech-decisions.md) | Keputusan teknis D-01 s/d D-15 |
| [`docs/bug-log.md`](./docs/bug-log.md) | Bug, penyebab, dan perbaikannya |
| [`docs/handoff.md`](./docs/handoff.md) | Catatan serah-terima antar sesi |
