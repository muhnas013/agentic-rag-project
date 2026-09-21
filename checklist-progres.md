# Checklist Progres Pengerjaan Project Agentic RAG

## Status umum
- [x] Project mulai didefinisikan
- [x] PRD dibaca dan dipahami
- [ ] Roadmap kerja dibuat
- [x] Infrastruktur dasar disiapkan
- [x] Backend utama berjalan
- [!] RAG minimal berfungsi (retrieval jalan; penyusunan jawaban menunggu LLM_API_KEY)
- [ ] Integrasi Ollama selesai
- [x] Integrasi PostgreSQL + pgvector selesai
- [ ] OCR tool selesai
- [ ] SQL tool selesai
- [ ] Frontend chat basic selesai
- [ ] Agent orchestrator dasar selesai
- [ ] Pengujian end-to-end dilakukan
- [ ] Dokumentasi teknis dibuat
- [ ] Project siap demo / presentasi

## Fase 1: Persiapan & Foundation
- [x] Review PRD dan scope project
- [x] Tentukan teknologi yang dipakai
- [x] Siapkan struktur folder project
- [x] Buat file environment/config dasar
- [x] Siapkan repository dan dokumentasi awal

## Fase 2: Backend Core
- [x] Setup FastAPI project
- [x] Konfigurasi CORS dan routing dasar
- [x] Setup PostgreSQL database
- [x] Setup pgvector extension
- [x] Buat model tabel chat history
- [x] Buat model tabel dokumen / embedding
- [x] Buat service upload dokumen
- [x] Buat proses embedding dokumen
- [x] Buat endpoint query RAG
- [x] Uji retrieval basic

## Fase 3: Integrasi LLM Lokal
- [ ] Setup Ollama
- [x] Tentukan model LLM + embedding (qwen2.5:7b + nomic-embed-text)
- [ ] Pull model LLM yang akan dipakai
- [ ] Integrasi FastAPI ke Ollama
- [ ] Uji prompt dasar ke model
- [ ] Uji RAG + LLM menghasilkan jawaban
- [ ] Optimasi prompt untuk jawaban yang lebih baik

## Fase 4: Agent Orchestrator
- [ ] Pilih framework agent (LangChain / tools-based)
- [ ] Definisikan tool RAG
- [ ] Definisikan tool OCR
- [ ] Definisikan tool SQL
- [ ] Agent dapat memilih tool berdasarkan pertanyaan
- [ ] Uji routing tool secara dasar
- [ ] Uji multi-tool workflow

## Fase 5: OCR & Data Terstruktur
- [ ] Setup PaddleOCR
- [ ] Buat OCR tool untuk gambar / dokumen image
- [ ] Uji ekstraksi teks dari gambar
- [ ] Integrasikan OCR dengan agent
- [ ] Setup PostgreSQL schema data sample
- [ ] Buat SQL tool untuk query data
- [ ] Uji query SQL via agent

## Fase 6: Frontend
- [ ] Setup Vite + React/Vue project
- [ ] Buat layout chat basic
- [ ] Buat input prompt dan upload file
- [ ] Integrasi API backend
- [ ] Tampilkan respons chat
- [ ] Tambahkan loading state dan error handling
- [ ] Uji UX dasar

## Fase 7: Testing & Stabilitas
- [ ] Uji endpoint backend
- [ ] Uji flow RAG end-to-end
- [ ] Uji OCR end-to-end
- [ ] Uji SQL query end-to-end
- [ ] Uji performance dasar
- [ ] Perbaiki bug yang ditemukan
- [ ] Simpan log / dokumentasi bug

## Fase 8: Demo & Finalization
- [ ] Siapkan demo scenario
- [ ] Cek semua fitur utama berjalan
- [ ] Buat README final
- [ ] Siapkan catatan deployment / run instruction
- [ ] Lakukan demo / review akhir

## Catatan update progres
Gunakan format berikut saat update status:
- [x] Item selesai
- [ ] Item belum selesai
- [!] Item sedang dikerjakan

Contoh:
- [!] Setup FastAPI project sedang dikerjakan
- [x] PostgreSQL + pgvector sudah siap
- [ ] RAG minimal belum diuji end-to-end

## Catatan penting
- Fokus utama saat ini: membangun MVP RAG yang berjalan terlebih dahulu.
- Setelah core flow stabil, baru menambahkan OCR, SQL, dan frontend yang lebih lengkap.
- Jika terjadi blocker, tulis di bagian catatan dan prioritas ulang.

## Log pengerjaan

### Fase 1 — Persiapan & Foundation · selesai (21 Sep 2026)

Hasil:
- Struktur folder dibuat sesuai PRD §6: `backend/{tools,services}/`,
  `frontend/src/{components,services}/`, `storage/{uploads,processed}/`, `docs/`.
- `.env.example` dan `.env` berisi konfigurasi database, Ollama, RAG, batas
  upload, dan security (JWT, allowlist tabel SQL Agent, query timeout).
- `.gitignore` memblokir `.env`, isi `storage/`, `node_modules/`, dan cache Python.
- `README.md` — ringkasan arsitektur, stack, struktur, dan catatan keamanan.
- `docs/tech-decisions.md` — teknologi terpilih beserta alasan dan hasil
  pemeriksaan mesin.
- Repository Git diinisialisasi, commit pertama dibuat.
  Diverifikasi: `.env` tidak ikut tertrack.

Pemeriksaan mesin: 24 core, RAM 15 GB, RTX 4060 8 GB, Docker 29.7.2 +
Compose 5.4.0, Node 26.7.0, psql client 18.4.

Keputusan yang menyimpang dari PRD (detail di `docs/tech-decisions.md`):
- **D-01** Backend berjalan di container `python:3.12-slim`. Host hanya punya
  Python 3.14.7, sedangkan `paddlepaddle` belum merilis wheel untuk versi itu.
- **D-02** Model LLM `llama3.1:8b` (PRD mencontohkan `llama3`), dipilih agar
  muat di VRAM 8 GB.

Blocker: tidak ada.

Belum dikerjakan (masuk fase berikutnya):
- Ollama belum terpasang di mesin → Fase 3.
- `docker-compose.yml` dan `backend/requirements.txt` → Fase 2.

### Pemilihan model · selesai (21 Sep 2026)

Dilakukan sebelum Fase 2 agar skema database dan konfigurasi tidak perlu
diulang di kemudian hari.

Hasil pengukuran mesin: RTX 4060 Laptop dengan 7,8 GB VRAM bebas,
i7-13700HX 16 core / 24 thread, RAM 15 GB (6,4 GB tersedia) + swap 30 GB,
disk bebas 139 GB.

| Peran     | Model                          | Unduh  | VRAM   |
|-----------|--------------------------------|--------|--------|
| LLM Agent | `qwen2.5:7b-instruct-q4_K_M`   | 4,7 GB | 5,2 GB |
| Embedding | `nomic-embed-text` (v1.5)      | 274 MB | 0,3 GB |
| **Total** |                                |        | **5,5 GB** dari 7,8 GB |

Sisa 2,3 GB. PaddleOCR sengaja dijalankan di CPU (`OCR_USE_GPU=false`)
agar tidak berebut VRAM; dengan 24 thread, OCR di CPU masih cepat.

Pertimbangan utama: keandalan *tool calling*, bukan ukuran model. Agent pada
PRD §14 harus memilih sendiri di antara `RAG_Search`, `Image_OCR`, dan
`SQL_Query`, sehingga model yang lemah pada tool calling akan menggagalkan
premis project. Qwen2.5 7B unggul pada tool calling dan bahasa Indonesia
dibanding Llama 3.1 8B, serta menyisakan penyangga VRAM lebih besar daripada
Qwen3 8B.

Alternatif yang ditolak: `qwen3:8b` (sisa VRAM hanya 0,7 GB),
`llama3.1:8b` (bahasa Indonesia lebih lemah), `qwen3:4b` (sering salah tool).

Kedua tag sudah diverifikasi tersedia di registry Ollama sebelum ditetapkan.

Perubahan konfigurasi:
- `OLLAMA_LLM_MODEL=qwen2.5:7b-instruct-q4_K_M` (sebelumnya `llama3.1:8b`)
- `OLLAMA_NUM_CTX=8192` ditambahkan — membatasi KV cache, cukup untuk system
  prompt, definisi tool, 4 potongan dokumen, dan riwayat percakapan
- `EMBEDDING_DIM=768` tetap, sehingga `VECTOR(768)` pada PRD §7.2 dipakai apa adanya

Risiko yang diterima dan mitigasinya:
- `nomic-embed-text` berorientasi bahasa Inggris (akurasi retrieval 57%
  berbanding 72% milik `bge-m3`), sehingga pada dokumen berbahasa Indonesia
  potongan relevan lebih sering tidak terambil. Dipilih karena sesuai default
  PRD dan hemat VRAM.
- Mitigasi: dimensi vektor dibaca dari `EMBEDDING_DIM`, tidak ditulis mati di
  kode. Bila uji retrieval Fase 7 mengecewakan, pindah ke `bge-m3` cukup ubah
  `.env` (`bge-m3` + `EMBEDDING_DIM=1024`), migrasi kolom, lalu embedding ulang.
  **Perlu dicek ulang saat Fase 7.**

Blocker: tidak ada. Ollama belum terpasang — pengunduhan model dilakukan di Fase 3.

### Fase 2 — Backend Core · selesai (21 Sep 2026)

Hasil, seluruhnya diverifikasi dengan container yang benar-benar berjalan:

**Infrastruktur**
- `docker-compose.yml` — service `postgres` (`pgvector/pgvector:pg16`, volume
  persisten `postgres_data`, healthcheck) dan `backend` (build dari
  `backend/Dockerfile`, `depends_on: service_healthy`).
- `backend/Dockerfile` — `python:3.12-slim` + `libmagic1`, dijalankan sebagai
  user non-root, `--reload` aktif karena `./backend` di-mount sebagai volume.
- `docker/postgres/init/` — dua skrip yang berjalan sekali saat volume kosong:
  mengaktifkan extension `vector` dan membuat user read-only `rag_readonly`.
- `.env` ditulis dari sudut pandang host; `docker-compose.yml` menimpa
  `DATABASE_URL` dan `OLLAMA_BASE_URL` untuk sudut pandang container.

**Kode backend**
- `config.py` — seluruh setting dibaca dari `.env` lewat pydantic-settings.
- `database.py` — dua engine terpisah (aplikasi dan SQL Agent read-only),
  `init_database()`, `check_database_connection()`.
- `models.py` — `chat_history` dan `documents` persis PRD §7, termasuk nama
  kolom `metadata` dan `VECTOR(768)`.
- `schemas.py`, `main.py` — tujuh endpoint (lihat README).
- `services/embedding_service.py`, `services/llm_service.py` — lapisan provider.
- `services/document_service.py` — validasi upload, ekstraksi, chunking,
  embedding, penyimpanan, pencarian kemiripan.
- `tests/test_document_service.py` — 14 test, semuanya lulus.

**Hasil pengujian**

| Yang diuji | Hasil |
|------------|-------|
| `GET /health` | `status: ok`, database `true`, extension vector `true` |
| Skema tabel | Cocok dengan PRD §7, kolom `embedding vector(768)` |
| Upload `.txt` | 1 chunk tersimpan |
| Upload `.pdf` | Teks terekstraksi, 1 chunk tersimpan |
| Upload `.md` panjang | Terpotong menjadi 8 chunk |
| Unggah ulang nama sama | Tetap 8 chunk — isi lama diganti, tidak menumpuk |
| Upload `.png` sah | `status: stored`, menunggu OCR Fase 5 |
| Upload `.exe` | Ditolak 400 — ekstensi di luar allowlist |
| PNG dinamai `.pdf` | Ditolak 400 — signature tidak cocok |
| PNG rusak | Ditolak 400 — MIME `application/octet-stream` |
| `POST /query` | Dokumen yang benar selalu peringkat 1 pada 3 pertanyaan uji |
| `POST /chat` tanpa key | 503 dengan pesan yang menyebut langkah perbaikannya |
| `GET /chat/history` | Urut dari pesan terlama, `session_id` kosong ditolak 422 |
| User `rag_readonly` | `SELECT` berhasil; `DELETE` dan `CREATE TABLE` ditolak |

**Keputusan baru** (detail di `docs/tech-decisions.md`):
- **D-06** Provider LLM dan embedding dapat ditukar lewat `.env`. Selama model
  lokal ditunda, LLM memakai Atria Dawn Preview (OpenAI-compatible, mendukung
  tool calling). Kembali ke Ollama di Fase 3 cukup mengubah dua baris `.env`.
- **D-07** `hash_stub` — embedding deterministik tanpa model, agar pipeline RAG
  bisa diuji sekarang. Tidak mewakili mutu retrieval sebenarnya.
- **D-08** Index HNSW jarak cosine pada `documents.embedding`.
- **D-09** Nama berkas unggahan diganti UUID; nama asli disimpan di database.

**Blocker:** tidak ada, tetapi ada dua hal yang masih menunggu:

1. `LLM_API_KEY` di `.env` masih kosong, sehingga `POST /chat` belum pernah
   menghasilkan jawaban sungguhan. Jalur retrieval-nya sendiri sudah terbukti
   lewat `POST /query`. Setelah key diisi: `docker compose restart backend`.
2. Embedding masih memakai `hash_stub`. Mutu retrieval yang sebenarnya baru
   bisa dinilai setelah `nomic-embed-text` tersedia di Fase 3.

**Catatan yang perlu diingat.** Dokumen yang sudah terlanjur diindeks dengan
`hash_stub` **wajib diunggah ulang** setelah pindah ke model embedding
sungguhan. Vektor dari dua model berbeda tidak sebanding, dan gejalanya
menipu: pencarian tetap mengembalikan hasil, hanya saja hasilnya acak.
Kolom `documents.metadata` menyimpan `embedding_model` untuk tiap potongan,
jadi baris lama bisa dikenali dengan:

```sql
SELECT DISTINCT filename, metadata->>'embedding_model' FROM documents;
```

---

**Menyambung pengerjaan:** ringkasan posisi, keputusan yang sudah diambil, dan
langkah berikutnya ada di `docs/handoff.md`.
