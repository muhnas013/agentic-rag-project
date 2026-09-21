Agentic RAG — Local AI System
Arsitektur dan roadmap pengembangan sistem Agentic RAG (Retrieval-Augmented Generation) berbasis FastAPI, LangChain, PostgreSQL + pgvector, PaddleOCR, Ollama, dan ViteJS.

1. Overview
Sistem ini dirancang sebagai Agentic RAG, sehingga LLM tidak hanya menjawab pertanyaan berdasarkan konteks yang diberikan, tetapi bertindak sebagai Agent / Orchestrator yang dapat memilih tool sesuai kebutuhan pertanyaan pengguna.

Contoh kemampuan:

Mencari informasi pada dokumen menggunakan RAG + VectorDB.
Membaca teks dari gambar menggunakan PaddleOCR.
Mengambil data terstruktur menggunakan PostgreSQL / SQL Tool.
Menggunakan Ollama sebagai Local LLM.
Menyimpan embedding menggunakan pgvector.
Menyediakan REST API menggunakan FastAPI.
Menyediakan antarmuka chat menggunakan ViteJS + React/Vue.
2. Tujuan Sistem
Tujuan utama pengembangan:

Membuat AI Assistant yang dapat berjalan secara lokal.
Mengurangi ketergantungan terhadap layanan AI cloud untuk data sensitif.
Memungkinkan Agent memilih sumber informasi secara otomatis.
Menggabungkan data tidak terstruktur, seperti PDF/gambar, dengan data terstruktur dari PostgreSQL.
Menyediakan fondasi sistem yang dapat dikembangkan menjadi aplikasi AI enterprise.
3. System Architecture
3.1 Alur Kerja
Alur utama sistem:

User Input

User mengirim pertanyaan.
User dapat mengunggah gambar atau dokumen.
API Gateway — FastAPI

Menerima request dari frontend.
Memvalidasi request.
Mengarahkan data ke Agent.
Agent Orchestrator

Dibangun menggunakan LangChain.
Menganalisis kebutuhan user.
Memilih tool yang relevan.
Tool Execution

RAG Tool → pencarian dokumen pada pgvector.
OCR Tool → membaca teks dari gambar menggunakan PaddleOCR.
SQL Tool → mengambil data terstruktur dari PostgreSQL.
Local LLM — Ollama

Mengolah pertanyaan dan hasil tool.
Membentuk jawaban akhir.
Frontend

Menampilkan jawaban kepada user.
3.2 Diagram Arsitektur
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND — ViteJS                         │
│                  React / Vue + Tailwind                      │
│                                                              │
│  Chat UI │ File Upload │ Markdown │ Loading State            │
└──────────────────────────────┬───────────────────────────────┘
                               │
                        REST API / JSON
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    BACKEND — FASTAPI                         │
│                                                              │
│              API Gateway / Request Handler                   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                  AGENT ORCHESTRATOR                          │
│                  LangChain / LlamaIndex                      │
│                                                              │
│        LLM menentukan Tool yang dibutuhkan                   │
└──────────────┬────────────────┬────────────────┬─────────────┘
               │                │                │
               ▼                ▼                ▼
      ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐
      │   TOOL RAG     │ │   TOOL OCR   │ │     TOOL SQL     │
      │                │ │              │ │                  │
      │ Similarity     │ │ PaddleOCR    │ │ PostgreSQL Query  │
      │ Search         │ │              │ │                  │
      └───────┬────────┘ └──────┬───────┘ └────────┬─────────┘
              │                 │                  │
              ▼                 ▼                  ▼
      ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐
      │ PostgreSQL     │ │ Image/File   │ │ PostgreSQL       │
      │ + pgvector     │ │              │ │ Relational Data  │
      └────────────────┘ └──────────────┘ └──────────────────┘
              │
              └────────────────┬─────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │   OLLAMA LOCAL LLM  │
                    │  Llama / Mistral     │
                    └──────────┬───────────┘
                               │
                               ▼
                         Final Response
4. Technology Stack
4.1 Frontend
Komponen	Teknologi
Framework	ViteJS
UI	React atau Vue
Styling	TailwindCSS
HTTP Client	Axios / Fetch API
Markdown	Markdown Renderer
4.2 Backend & AI
Komponen	Teknologi
Programming Language	Python 3.10+
API Framework	FastAPI
ASGI Server	Uvicorn
Agent Framework	LangChain
Local LLM	Ollama
LLM Model	Llama / Mistral
Embedding	nomic-embed-text / BGE-M3
OCR	PaddleOCR
ORM	SQLAlchemy
4.3 Database
Komponen	Teknologi
Relational Database	PostgreSQL
Vector Database	pgvector
Chat History	PostgreSQL
Document Embedding	pgvector
5. Hardware Requirements
Minimum — Local Development
CPU: 4 Core
RAM: 16 GB
Storage: 50 GB+ free space
GPU: Optional
OS: Windows / Linux / macOS
Recommended
CPU: 8 Core+
RAM: 32 GB
GPU: NVIDIA dengan VRAM 8 GB+
Storage: SSD 100 GB+
Docker: Recommended
GPU sangat membantu untuk Local LLM dan OCR. Tanpa GPU, sistem tetap dapat berjalan menggunakan CPU tetapi inference dan OCR dapat menjadi lebih lambat.

6. Project Structure
Struktur project yang direkomendasikan:

my-agentic-rag/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatBox.jsx
│   │   │   ├── UploadButton.jsx
│   │   │   └── MessageBubble.jsx
│   │   │
│   │   ├── services/
│   │   │   └── api.js
│   │   │
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── config.py
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── ocr_tool.py
│   │   ├── rag_tool.py
│   │   └── sql_tool.py
│   │
│   ├── services/
│   │   ├── embedding_service.py
│   │   ├── document_service.py
│   │   └── llm_service.py
│   │
│   ├── requirements.txt
│   └── .env
│
├── storage/
│   ├── uploads/
│   └── processed/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
7. Database Design
7.1 Chat History
Contoh tabel:

CREATE TABLE chat_history (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
Role dapat berupa:

user
assistant
system
tool
7.2 Documents
Contoh tabel untuk dokumen:

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
Dimensi VECTOR(768) harus disesuaikan dengan dimensi embedding model yang digunakan.

8. Agent Tools
Agent memiliki beberapa tool utama.

Tool 1 — RAG Search
Digunakan ketika user bertanya mengenai informasi yang terdapat pada dokumen.

Contoh:

User:
"Menurut dokumen kebijakan perusahaan, berapa lama masa retensi dokumen?"

Agent:
→ Memilih RAG Search
→ Query embedding
→ Similarity Search
→ Mengambil context
→ LLM menyusun jawaban
Tool 2 — OCR
Digunakan ketika user mengunggah gambar dan membutuhkan informasi dari gambar.

Contoh:

User:
"Berapa total transaksi pada struk ini?"

Agent:
→ Memilih Image OCR
→ PaddleOCR membaca gambar
→ OCR menghasilkan teks
→ LLM memahami hasil OCR
→ Menghasilkan jawaban
Tool 3 — SQL
Digunakan untuk pertanyaan yang membutuhkan data terstruktur.

Contoh:

User:
"Berapa jumlah pertanyaan yang masuk hari ini?"

Agent:
→ Memilih SQL Tool
→ Membuat query PostgreSQL
→ Menjalankan query
→ Mengambil hasil
→ LLM menyusun jawaban
SQL Tool sebaiknya menggunakan mekanisme keamanan seperti allowlist tabel/kolom, validasi query, read-only database user, timeout, dan pembatasan query agar Agent tidak dapat melakukan operasi destruktif.

9. RAG Pipeline
Pipeline RAG:

              DOCUMENT
                  │
                  ▼
          Document Loader
                  │
                  ▼
              Cleaning
                  │
                  ▼
             Chunking
                  │
                  ▼
          Embedding Model
                  │
                  ▼
          Vector Embedding
                  │
                  ▼
          PostgreSQL pgvector
                  │
                  │
            User Question
                  │
                  ▼
          Question Embedding
                  │
                  ▼
          Similarity Search
                  │
                  ▼
        Relevant Document Chunks
                  │
                  ▼
                 LLM
                  │
                  ▼
              Answer
10. OCR Pipeline
User Upload Image
        │
        ▼
    FastAPI
        │
        ▼
   Image Validation
        │
        ▼
     PaddleOCR
        │
        ▼
 Extracted Text
        │
        ▼
 Agent / LLM
        │
        ▼
 Final Answer
11. Agent Workflow
Secara konseptual:

User Question
      │
      ▼
┌───────────────────────┐
│     Agent / LLM       │
│                       │
│ "Tool apa yang cocok?"│
└───────────┬───────────┘
            │
     ┌──────┼──────┐
     │      │      │
     ▼      ▼      ▼
    RAG    OCR    SQL
     │      │      │
     └──────┼──────┘
            ▼
       Tool Result
            │
            ▼
        Context
            │
            ▼
        Local LLM
            │
            ▼
       Final Answer
12. Development Phases
Fase 1 — Infrastruktur & Database
Estimasi: Hari 1–2

Task
Install PostgreSQL.
Aktifkan pgvector.
Membuat database.
Membuat tabel chat_history.
Membuat tabel documents.
Install Ollama.
Menyiapkan model LLM.
Menyiapkan embedding model.
Contoh Docker PostgreSQL + pgvector:

docker run -d \
  --name agentic-rag-db \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=mysecretpassword \
  ankane/pgvector
Contoh Ollama:

ollama run llama3
Embedding:

ollama pull nomic-embed-text
13. Fase 2 — Backend Core & AI Tools
Estimasi: Hari 3–5

FastAPI
Endpoint awal:

POST /chat
POST /upload
POST /documents
GET  /chat/history
GET  /health
OCR
Implementasi:

Image
  ↓
PaddleOCR
  ↓
Extracted Text
  ↓
Agent
RAG
Tahapan:

PDF / TXT
   ↓
Document Loader
   ↓
Text Splitter
   ↓
Embedding
   ↓
pgvector
LangChain Tools
Fungsi seperti:

@tool
def rag_search(query: str):
    ...

@tool
def image_ocr(image_path: str):
    ...

@tool
def sql_query(query: str):
    ...
14. Fase 3 — Agentic System
Estimasi: Hari 6–7

Agent diberikan tools:

RAG_Search
Image_OCR
SQL_Query
Contoh system prompt:

Kamu adalah AI Assistant berbasis Agentic RAG.

Kamu memiliki beberapa tools:

1. RAG_Search
   Digunakan untuk mencari informasi dari dokumen yang tersimpan
   di knowledge base.

2. Image_OCR
   Digunakan untuk membaca teks dari gambar yang diberikan user.

3. SQL_Query
   Digunakan untuk mengambil data terstruktur dari database.

Pilih tool berdasarkan kebutuhan pertanyaan user.

Jangan menggunakan tool yang tidak diperlukan.

Jika informasi tidak tersedia, katakan bahwa informasi tersebut
tidak ditemukan.
15. Fase 4 — Frontend Development
Estimasi: Hari 8–9

Inisialisasi:

npm create vite@latest frontend -- --template react
Install dependency:

cd frontend
npm install
npm install axios
Fitur UI
Frontend minimal memiliki:

Chat interface.
Message bubble.
Text input.
File upload.
Loading indicator.
Markdown rendering.
Error handling.
Chat history.
Source/reference information.
Contoh UI:

┌───────────────────────────────────────────────┐
│              Agentic RAG Assistant            │
├───────────────────────────────────────────────┤
│                                               │
│ User: Apa isi dokumen kebijakan?              │
│                                               │
│ AI: Berdasarkan dokumen...                    │
│                                               │
│ [RAG Source: policy.pdf]                      │
│                                               │
├───────────────────────────────────────────────┤
│ 📎  Tulis pertanyaan...                 [Send]│
└───────────────────────────────────────────────┘
16. Fase 5 — Testing & Tuning
Estimasi: Hari 10

RAG Test
Input:

Masukkan dokumen perusahaan.
Pertanyaan:

"Menurut dokumen tersebut, apa kebijakan cuti karyawan?"
Validasi:

Agent memilih RAG.
Dokumen relevan ditemukan.
Jawaban sesuai context.
Tidak membuat informasi yang tidak ada.
OCR Test
Upload gambar yang berisi teks.

Contoh:

"Total transaksi berapa?"
Validasi:

Agent memilih OCR.
PaddleOCR berhasil membaca teks.
Nilai yang terbaca sesuai gambar.
LLM menghasilkan jawaban berdasarkan hasil OCR.
SQL Test
Contoh:

"Berapa jumlah chat yang masuk hari ini?"
Validasi:

Agent memilih SQL.
Query valid.
Query bersifat read-only.
Hasil sesuai database.
17. Testing Matrix
Test Case	Input	Expected Tool	Expected Result
RAG-001	Pertanyaan tentang PDF	RAG	Jawaban dari dokumen
OCR-001	Upload gambar	OCR	Teks berhasil diekstrak
SQL-001	Pertanyaan statistik	SQL	Data dari PostgreSQL
AGENT-001	Pertanyaan umum	LLM	Jawaban langsung
AGENT-002	Pertanyaan ambigu	Agent	Memilih tool sesuai context
SEC-001	SQL destruktif	SQL	Ditolak
SEC-002	Dokumen tidak ditemukan	RAG	Informasi tidak ditemukan
18. Security Considerations
Karena sistem dapat mengakses dokumen, database, dan file pengguna, keamanan harus dirancang sejak awal.

Authentication
Gunakan:

JWT / Session Authentication
Authorization
Pisahkan permission:

ADMIN
USER
READ_ONLY
Database Security
Rekomendasi:

Gunakan database user khusus aplikasi.
Gunakan user read-only untuk SQL Agent.
Jangan memberikan permission DROP, DELETE, atau UPDATE kepada SQL Agent kecuali benar-benar diperlukan.
Gunakan parameterized query.
Terapkan query timeout.
Batasi tabel yang boleh diakses Agent.
File Upload Security
Validasi:

File Extension
MIME Type
File Size
File Signature
Tambahkan antivirus/malware scanning jika sistem digunakan pada lingkungan produksi.

Prompt Injection
Dokumen yang diambil dari RAG harus dianggap sebagai data, bukan instruksi.

Contoh:

User Question
      ↓
Agent
      ↓
Retrieve Document
      ↓
Treat document as untrusted context
      ↓
Generate Answer
19. Environment Variables
Buat .env:

APP_ENV=development

DATABASE_URL=postgresql://postgres:mysecretpassword@localhost:5432/agentic_rag

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

UPLOAD_DIR=./storage/uploads

CORS_ORIGINS=http://localhost:5173
Jangan commit .env ke Git.

Tambahkan:

.env
__pycache__/
*.pyc
node_modules/
storage/uploads/
storage/processed/
20. API Design
Health Check
GET /health
Response:

{
  "status": "ok"
}
Chat
POST /chat
Request:

{
  "session_id": "session-001",
  "message": "Apa isi dokumen kebijakan?"
}
Response:

{
  "answer": "Berdasarkan dokumen...",
  "tool_used": "rag_search",
  "sources": [
    {
      "filename": "policy.pdf"
    }
  ]
}
Upload
POST /upload
Form-data:

file=<document-or-image>
Response:

{
  "filename": "document.pdf",
  "status": "processed"
}
21. Docker Architecture
Production/development dapat dikembangkan menjadi:

                 ┌───────────────┐
                 │    Nginx      │
                 └───────┬───────┘
                         │
              ┌──────────▼──────────┐
              │      Frontend       │
              │   ViteJS / React    │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │       FastAPI       │
              │       Backend       │
              └───────┬─────┬───────┘
                      │     │
             ┌────────▼─┐ ┌─▼──────────┐
             │PostgreSQL│ │   Ollama   │
             │+pgvector │ │ Local LLM  │
             └──────────┘ └────────────┘
22. Recommended docker-compose
Contoh struktur:

services:

  postgres:
    image: pgvector/pgvector:pg16
    container_name: agentic-rag-db
    environment:
      POSTGRES_DB: agentic_rag
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: mysecretpassword
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    container_name: agentic-rag-backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres

volumes:
  postgres_data:
Ollama dapat dijalankan di host machine atau sebagai container terpisah, tergantung kebutuhan deployment dan akses GPU.

23. Development Roadmap
PHASE 1
Infrastructure
    │
    ├── PostgreSQL
    ├── pgvector
    └── Ollama
    │
    ▼
PHASE 2
Backend
    │
    ├── FastAPI
    ├── RAG
    ├── OCR
    └── SQL Tool
    │
    ▼
PHASE 3
Agent
    │
    ├── Tool Selection
    ├── Prompt
    └── Orchestration
    │
    ▼
PHASE 4
Frontend
    │
    ├── Chat UI
    ├── Upload
    └── API Integration
    │
    ▼
PHASE 5
Testing
    │
    ├── RAG
    ├── OCR
    ├── SQL
    ├── Security
    └── Performance
    │
    ▼
PRODUCTION
24. Definition of Done
Sistem dapat dianggap mencapai MVP apabila:

Backend
 FastAPI berjalan.
 PostgreSQL terhubung.
 pgvector aktif.
 Ollama berjalan.
 RAG berhasil.
 OCR berhasil.
 SQL Tool berhasil.
 Agent dapat memilih tool.
Frontend
 Chat UI berjalan.
 User dapat mengirim pertanyaan.
 User dapat upload gambar.
 User dapat upload dokumen.
 Response AI tampil.
 Loading state tersedia.
 Error handling tersedia.
Security
 Authentication.
 Authorization.
 File validation.
 SQL restriction.
 Prompt injection mitigation.
 .env tidak masuk Git.
25. Future Development
Setelah MVP berhasil, sistem dapat dikembangkan menjadi:

Multi-Agent
                    Supervisor Agent
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
     RAG Agent        OCR Agent       SQL Agent
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                     Final Answer
Advanced Features
Hybrid Search: BM25 + Vector Search.
Reranking.
Query rewriting.
Conversation memory.
Streaming response.
Multi-document retrieval.
Document versioning.
Citation / source tracking.
User-specific knowledge base.
Role-based access control.
Observability dan tracing.
Evaluation pipeline.
LLM guardrails.
Redis untuk caching.
Celery/RQ untuk background processing.
MinIO/S3 untuk object storage.
Kubernetes untuk deployment skala besar.
26. Kesimpulan
Arsitektur Agentic RAG ini menggabungkan:

ViteJS
   +
FastAPI
   +
LangChain
   +
PostgreSQL
   +
pgvector
   +
PaddleOCR
   +
Ollama
   +
Local LLM
Keunggulan pendekatan ini adalah Agent dapat menentukan sumber informasi yang sesuai dengan kebutuhan user:

Question
   │
   ▼
Agent
   │
   ├── Dokumen → RAG / pgvector
   │
   ├── Gambar  → PaddleOCR
   │
   └── Data    → PostgreSQL
   │
   ▼
Local LLM
   │
   ▼
Answer
Dengan pendekatan modular ini, sistem dapat dimulai sebagai MVP lokal dan kemudian dikembangkan menjadi platform Enterprise Agentic AI dengan keamanan, observability, multi-agent orchestration, dan integrasi berbagai sumber data.s