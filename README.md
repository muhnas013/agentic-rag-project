# Agentic RAG — Local AI System

Sistem AI Assistant yang berjalan sepenuhnya di mesin lokal. LLM bertindak
sebagai **Agent** yang memilih tool sesuai kebutuhan pertanyaan: mencari di
dokumen (RAG), membaca teks dari gambar (OCR), atau mengambil data terstruktur
(SQL).

Spesifikasi lengkap ada di [`prd.md`](./prd.md).
Progres pengerjaan dicatat di [`checklist-progres.md`](./checklist-progres.md).

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
| Embedding | Ollama — `nomic-embed-text` (768 dimensi)      |
| OCR       | PaddleOCR                                      |
| Database  | PostgreSQL 16 + pgvector                       |

Alasan tiap pilihan: [`docs/tech-decisions.md`](./docs/tech-decisions.md).

## Struktur project

```
praktek-ai-engineer/
├── backend/            # FastAPI, agent, tools, services
│   ├── tools/          # rag_tool, ocr_tool, sql_tool
│   └── services/       # embedding, document, llm
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

> Backend dan database berjalan di Docker; Ollama berjalan di host.
> Instruksi lengkap ditambahkan seiring tiap fase selesai.

```bash
cp .env.example .env    # lalu sesuaikan kredensial
```

Langkah berikutnya menyusul pada Fase 2 (backend + database).

## Keamanan

Sesuai PRD §18, sistem menerapkan:

- SQL Tool memakai user database **read-only** dengan allowlist tabel dan timeout
- Validasi ekstensi, MIME type, ukuran, dan signature pada setiap file upload
- Dokumen hasil retrieval diperlakukan sebagai **data**, bukan instruksi
  (mitigasi prompt injection)
- `.env` tidak pernah masuk ke Git
