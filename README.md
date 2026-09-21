# Agentic RAG — Local AI System

Sistem AI Assistant yang berjalan sepenuhnya di mesin lokal. LLM bertindak
sebagai **Agent** yang memilih tool sesuai kebutuhan pertanyaan: mencari di
dokumen (RAG), membaca teks dari gambar (OCR), atau mengambil data terstruktur
(SQL).

Spesifikasi lengkap ada di [`prd.md`](./prd.md).
Progres pengerjaan dicatat di [`checklist-progres.md`](./checklist-progres.md).
Untuk menyambung pengerjaan, baca [`docs/handoff.md`](./docs/handoff.md).

## Arsitektur singkat

```
Frontend (Vite + React)
        │  REST / JSON
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

## Stack

| Lapisan   | Teknologi                                      |
|-----------|------------------------------------------------|
| Frontend  | ViteJS, React, TailwindCSS, Axios              |
| Backend   | Python 3.12, FastAPI, Uvicorn, SQLAlchemy      |
| Agent     | LangChain                                      |
| LLM       | Ollama — `qwen2.5:7b-instruct-q4_K_M`          |
| LLM (sementara) | Atria Dawn Preview lewat API, selama model lokal belum diunduh |
| Embedding | Ollama — `nomic-embed-text` (768 dimensi)      |
| OCR       | PaddleOCR                                      |
| Database  | PostgreSQL 16 + pgvector                       |

Alasan tiap pilihan: [`docs/tech-decisions.md`](./docs/tech-decisions.md).

## Struktur project

```
praktek-ai-engineer/
├── backend/            # FastAPI, agent, tools, services
│   ├── main.py         # endpoint REST
│   ├── config.py       # seluruh setting dibaca dari .env
│   ├── database.py     # dua engine: aplikasi dan SQL Agent read-only
│   ├── models.py       # tabel chat_history dan documents
│   ├── schemas.py      # skema request/response
│   ├── tools/          # rag_tool, ocr_tool, sql_tool (Fase 4-5)
│   ├── services/       # embedding, document, llm
│   └── tests/
├── docker/postgres/init/   # extension vector + user read-only
├── frontend/           # Vite + React chat UI
├── storage/
│   ├── uploads/        # file mentah dari user
│   └── processed/      # hasil olahan
├── docs/               # catatan teknis
├── prd.md
└── checklist-progres.md
```

## Persyaratan

- Docker + Docker Compose
- Node.js 18+ (untuk frontend)
- Ollama di host machine
- GPU NVIDIA 8 GB VRAM (opsional, tetapi mempercepat LLM dan OCR)

### Model yang perlu diunduh

```bash
ollama pull qwen2.5:7b-instruct-q4_K_M   # 4,7 GB — LLM Agent
ollama pull nomic-embed-text             # 274 MB — embedding RAG
```

Keduanya residen bersamaan di VRAM saat RAG berjalan: ±5,5 GB dari 8 GB.

## Cara menjalankan

Backend dan database berjalan di Docker; Ollama nanti berjalan di host.

```bash
cp .env.example .env    # lalu sesuaikan kredensial
docker compose up -d    # PostgreSQL + backend
curl localhost:8000/health
```

Dokumentasi API interaktif: <http://localhost:8000/docs>.

Perintah yang sering dipakai:

```bash
docker compose logs -f backend          # ikuti log
docker compose up -d backend            # muat ulang setelah .env berubah
                                        # (restart TIDAK membaca ulang .env)
docker compose exec -w /app backend python -m pytest backend/tests -q
docker compose down                     # berhenti (data tetap tersimpan)
docker compose down -v                  # berhenti dan HAPUS isi database
```

Kode di `./backend` di-mount sebagai volume, jadi perubahan kode langsung
dimuat ulang tanpa perlu build ulang. Perubahan `.env` dan `requirements.txt`
tetap memerlukan `restart` atau `build`.

### Endpoint yang sudah ada

| Method | Path            | Keterangan                                   |
|--------|-----------------|----------------------------------------------|
| GET    | `/health`       | Status database, extension vector, dan model |
| POST   | `/upload`       | Unggah `.pdf` `.txt` `.md` lalu diolah jadi embedding; gambar hanya disimpan sampai Fase 5 |
| POST   | `/documents`    | Tambah dokumen dari teks langsung            |
| GET    | `/documents`    | Daftar dokumen terindeks + jumlah potongan   |
| POST   | `/query`        | Pencarian RAG mentah, tanpa LLM              |
| POST   | `/chat`         | Jawaban berbasis dokumen                     |
| GET    | `/chat/history` | Riwayat percakapan satu sesi                 |

`/query` sengaja dipisah dari `/chat`: bila jawaban keliru, endpoint itu
menunjukkan apakah penyebabnya ada pada pencarian atau pada model.

### Provider model

Target akhirnya Ollama sesuai PRD. Selama model lokal belum diunduh, LLM
dilayani API yang OpenAI-compatible, diatur lewat `.env`:

```
LLM_PROVIDER=openai_compatible      # ollama | openai_compatible
EMBEDDING_PROVIDER=hash_stub        # ollama | openai_compatible | hash_stub
LLM_API_KEY=atr_...                 # isi di sini
```

`hash_stub` adalah embedding tanpa model, khusus pengembangan: cukup untuk
menguji pipeline RAG, **tidak** untuk menilai mutu retrieval. Beralih ke
Ollama pada Fase 3 cukup mengubah dua variabel pertama menjadi `ollama`.

> **Penting.** Dokumen yang diindeks dengan satu model embedding harus
> diunggah ulang setelah berganti model. Vektor dua model berbeda tidak
> sebanding, dan pencarian tetap mengembalikan hasil — hanya saja hasilnya
> acak, sehingga kesalahan ini tidak terlihat kecuali sengaja diuji.

## Keamanan

Sesuai PRD §18, sistem menerapkan:

- SQL Tool memakai user database **read-only** dengan allowlist tabel dan timeout
- Validasi ekstensi, MIME type, ukuran, dan signature pada setiap file upload
- Dokumen hasil retrieval diperlakukan sebagai **data**, bukan instruksi
  (mitigasi prompt injection)
- `.env` tidak pernah masuk ke Git
