# Catatan Serah-Terima Sesi

Terakhir diperbarui: 21 September 2026

Dokumen ini merangkum posisi pengerjaan agar sesi berikutnya bisa langsung
menyambung tanpa mengulang pembahasan.

## Posisi saat ini

**Fase 1 dan Fase 2 selesai. Fase 3 selesai sebagian — semua item yang
tidak memerlukan unduhan model sudah dikerjakan dan terbukti.
Berikutnya: Fase 4 — Agent Orchestrator.**

Rincian tiap item ada di `checklist-progres.md` pada section "Log pengerjaan".
Itu sumber kebenaran status, bukan dokumen ini.

Yang sudah berjalan dan terbukti: PostgreSQL + pgvector, tujuh endpoint
FastAPI, validasi upload, pipeline dokumen sampai tersimpan sebagai vektor,
pencarian kemiripan, penyusunan jawaban oleh LLM, pertahanan prompt injection,
dan **tool calling (4 dari 4 tepat)** — sehingga Fase 4 tidak lagi berisiko.

Yang belum terbukti: jalur Ollama (kodenya ada, belum pernah dieksekusi) dan
mutu retrieval yang sebenarnya, karena embedding masih `hash_stub`.

## Yang sudah ada di repo

```
praktek-ai-engineer/
├── prd.md                    spesifikasi (tidak diubah)
├── checklist-progres.md      status + log pengerjaan  <- baca ini dulu
├── README.md                 arsitektur, endpoint, cara jalan
├── docker-compose.yml        postgres + backend
├── .env / .env.example       konfigurasi (.env tidak masuk Git)
├── docker/postgres/init/     extension vector + user read-only
├── backend/
│   ├── Dockerfile, requirements.txt
│   ├── main.py config.py database.py models.py schemas.py
│   ├── services/  embedding_service, llm_service, document_service
│   ├── tools/     masih kosong, diisi Fase 4-5
│   └── tests/     14 test, semuanya lulus
├── frontend/src/{components,services}/  masih kosong
├── storage/{uploads,processed}/
└── docs/  tech-decisions.md (D-01 s/d D-09), handoff.md
```

Git ada di branch `main`, belum ada remote.

## Satu hal yang masih menunggu: embedding masih `hash_stub`

`LLM_API_KEY` sudah diisi dan terbukti bekerja — `POST /chat` menghasilkan
jawaban benar beserta sumbernya. Yang tersisa adalah embedding.

`hash_stub` hanya mencocokkan kata, bukan makna. Pipeline RAG terbukti benar,
tetapi mutu retrieval belum bisa dinilai sama sekali. Dokumen uji sengaja
dibuat berbeda topik agar pencarian berbasis kata pun cukup memisahkannya;
pada dokumen nyata yang bertopik mirip, `hash_stub` akan sering keliru.

**Dokumen yang sudah diindeks wajib diunggah ulang setelah berganti ke model
embedding sungguhan.** Vektor dari dua model berbeda tidak sebanding, dan
gejalanya menipu: pencarian tetap mengembalikan hasil, hanya saja hasilnya
acak. Baris lama bisa dikenali lewat metadata:

```sql
SELECT DISTINCT filename, metadata->>'embedding_model' FROM documents;
```

## Cara memuat ulang konfigurasi — jangan pakai `restart`

`docker compose restart` memakai ulang environment yang dibekukan saat
container dibuat, sehingga perubahan `.env` **tidak** terbaca. Gejalanya
membingungkan: `.env` sudah benar tetapi aplikasi bersikeras nilainya kosong.

```bash
docker compose up -d backend    # benar — container dibuat ulang
docker compose restart backend  # TIDAK membaca ulang .env
```

## Langkah berikutnya — Fase 4: Agent Orchestrator

Sesuai `checklist-progres.md`:

1. Pilih framework agent — PRD §4.2 menyebut LangChain
2. Definisikan tool `RAG_Search`, `Image_OCR`, `SQL_Query` (PRD §14)
3. Agent memilih tool sendiri berdasarkan pertanyaan
4. Uji routing tool, lalu uji alur multi-tool

Sudah terbukti pada Fase 3: provider LLM memilih tool yang tepat pada empat
kasus uji dan mengisi argumennya dengan benar, termasuk tahu kapan tidak perlu
tool sama sekali. `llm_service.chat()` sudah menerima parameter `tools` dan
menyeragamkan `tool_calls` dari kedua provider, jadi pondasinya siap.

Catatan: `Image_OCR` baru bisa benar-benar berjalan setelah PaddleOCR dipasang
di Fase 5, dan `SQL_Query` memakai koneksi read-only yang sudah disiapkan pada
Fase 2. Pada Fase 4 keduanya bisa dibuat sebagai tool yang mengembalikan pesan
"belum tersedia", supaya routing-nya tetap dapat diuji lebih dulu.

### Menyelesaikan sisa Fase 3 (kapan pun Ollama dipasang)

1. Pasang Ollama di host
2. `ollama pull qwen2.5:7b-instruct-q4_K_M` (4,7 GB)
   dan `ollama pull nomic-embed-text` (274 MB)
3. Ubah `.env`: `LLM_PROVIDER=ollama`, `EMBEDDING_PROVIDER=ollama`
4. `docker compose up -d backend`, lalu cek `GET /health`
5. Unggah ulang seluruh dokumen (lihat peringatan di atas)
6. Bandingkan hasil `POST /query` dengan catatan Fase 3 untuk menilai
   seberapa besar `hash_stub` menyesatkan

## Keputusan yang sudah diambil

| Kode | Keputusan | Inti alasan |
|------|-----------|-------------|
| D-01 | Backend di Docker `python:3.12-slim` | Host hanya punya Python 3.14, `paddlepaddle` belum punya wheel-nya |
| D-02 | LLM `qwen2.5:7b-instruct-q4_K_M` | Tool calling andal + bahasa Indonesia kuat, sisa VRAM 2,3 GB |
| D-02b | Embedding `nomic-embed-text` (768) | Sesuai default PRD, hemat VRAM — **ada risiko, lihat bawah** |
| D-03 | Ollama di host, bukan container | Akses GPU langsung tanpa container toolkit |
| D-04 | Driver `psycopg` v3 | Aktif dikembangkan, didukung penuh SQLAlchemy 2.x |
| D-05 | Dua koneksi database terpisah | SQL Tool pakai user read-only (PRD §18) |
| D-06 | Provider LLM/embedding ditukar lewat `.env` | Fase 2 tidak perlu menunggu unduhan model 5 GB |
| D-07 | `hash_stub` embedding pengembangan | Pipeline RAG bisa diuji tanpa model apa pun |
| D-08 | Index HNSW jarak cosine | Tidak perlu dibangun ulang saat data bertambah |
| D-09 | Nama berkas unggahan diganti UUID | Menutup path traversal dan tabrakan nama |
| D-10 | Ambang relevansi relatif, bukan angka mati | Rentang skor tiap model embedding berbeda |

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

**Skrip init PostgreSQL hanya jalan sekali.** Isi `docker/postgres/init/`
dieksekusi saat volume `postgres_data` masih kosong. Bila skripnya diubah,
perubahan itu baru berlaku setelah `docker compose down -v` — yang juga
menghapus seluruh data.

**`.env` tidak ikut Git.** Bila project dipindah ke mesin lain, salin `.env`
secara manual atau buat ulang dari `.env.example`.

## Cara memulai sesi berikutnya

Jalankan `claude` di `/home/nzrl4h/praktek-ai-engineer`, lalu sampaikan
kira-kira: *"lanjutkan Fase 3 Integrasi LLM Lokal, baca dulu docs/handoff.md
dan checklist-progres.md"*.
