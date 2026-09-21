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

### D-06 — Provider LLM dan embedding dapat ditukar lewat `.env`

**Masalah.** PRD §4.2 menetapkan Ollama sebagai penyedia LLM dan embedding,
tetapi pengunduhan model lokal (4,7 GB + 274 MB) ditunda sampai Fase 3.
Menunggu unduhan selesai akan menghentikan seluruh pengerjaan Fase 2.

**Keputusan.** `llm_service.py` dan `embedding_service.py` memakai kelas
abstrak `LLMBackend` dan `EmbeddingBackend` dengan implementasi yang dipilih
saat proses start, berdasarkan `LLM_PROVIDER` dan `EMBEDDING_PROVIDER` di
`.env`. Balasan tiap provider diseragamkan menjadi `ChatResponse`, termasuk
bagian `tool_calls`, sehingga Agent Orchestrator pada Fase 4 tidak perlu
mengetahui provider mana yang sedang aktif.

Selama model lokal belum ada, LLM dilayani **Atria Dawn Preview**
(`https://api.atria-asi.ai/v1`, model `Atria-Dawn-Preview`). Antarmukanya
OpenAI-compatible dan mendukung *tool calling*, sehingga premis PRD §14 —
Agent memilih sendiri di antara tiga tool — tetap dapat diuji.

**Kembali ke Ollama pada Fase 3** cukup mengubah dua baris `.env`:

```
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
```

**Konsekuensi.** Ada satu lapisan tambahan yang tidak disebut PRD. Imbalannya,
pengujian Fase 2 tidak bergantung pada unduhan model, dan lapisan yang sama
nanti dipakai bila Ollama sedang mati sehingga sistem butuh cadangan.

**Catatan penting.** Atria **tidak** menyediakan endpoint `/v1/embeddings`,
jadi provider ini hanya melayani LLM. Embedding tetap memerlukan Ollama
(Fase 3), layanan API lain, atau `hash_stub` di bawah.

### D-07 — `hash_stub`: embedding pengembangan tanpa model

**Masalah.** Seluruh pipeline RAG — chunking, penyimpanan, pencarian
pgvector, penyusunan konteks — tidak dapat diuji tanpa embedding, sedangkan
tidak ada satu pun model embedding yang tersedia pada Fase 2.

**Keputusan.** Ditambahkan provider ketiga `hash_stub`: setiap kata dipetakan
ke satu dimensi lewat hash BLAKE2b, dihitung frekuensinya, lalu vektornya
dinormalisasi. Hasilnya deterministik, berdimensi `EMBEDDING_DIM`, dan tidak
memerlukan jaringan maupun GPU.

**Batasnya harus disadari.** Yang ditangkap hanyalah kesamaan kata, bukan
kesamaan makna: "mobil" dan "kendaraan" dianggap tidak berhubungan sama
sekali. Karena itu `hash_stub` **tidak boleh** dipakai menilai mutu retrieval —
penilaian itu dikerjakan pada Fase 7 dengan model embedding sebenarnya.
Gunanya semata-mata memastikan pipa datanya benar.

### D-08 — Index HNSW dengan jarak cosine pada `documents.embedding`

PRD §7.2 tidak menyebut index. Tanpa index, pencarian kemiripan memindai
seluruh tabel; jumlah baris tumbuh cepat karena satu dokumen menghasilkan
banyak potongan.

Dipilih **HNSW** (bukan IVFFlat) karena tidak memerlukan pelatihan ulang saat
data bertambah — IVFFlat perlu dibangun ulang setelah jumlah baris berubah
banyak. Jarak **cosine** dipakai karena seluruh provider embedding di sini
menormalisasi panjang vektornya, sehingga arah vektor yang menentukan
kemiripan, bukan besarannya.

### D-09 — Nama berkas unggahan diganti UUID

Nama asli dari pengguna tidak pernah dipakai sebagai nama berkas di disk.
Berkas disimpan sebagai `<uuid>.<ekstensi>` di `storage/uploads/`, sedangkan
nama aslinya disimpan di kolom `documents.filename` dan metadata.

Alasannya dua: nama seperti `../../etc/passwd` menjadi tidak berbahaya, dan
dua pengguna yang mengunggah `laporan.pdf` tidak saling menimpa berkas.

### D-10 — Ambang relevansi retrieval ditetapkan relatif, bukan angka mati

**Masalah.** Pencarian kemiripan selalu mengembalikan sebanyak `RAG_TOP_K`
baris, tanpa peduli apakah barisnya nyambung dengan pertanyaan. Pada pengujian
Fase 3, dua dari empat potongan yang terkirim ke LLM berskor 0,0 — sama sekali
tidak relevan. Potongan seperti itu memakan jatah konteks yang terbatas
(8K token, keputusan D-02) dan berpotensi mengalihkan perhatian model.

**Keputusan.** `filter_relevant()` membuang potongan yang skornya di bawah
`RAG_MIN_SCORE_RATIO` dikali skor potongan terbaik. Nilai bawaannya `0.5`.

Ambang **relatif**, bukan angka mutlak, karena setiap model embedding punya
rentang skor sendiri. Pada `hash_stub` potongan yang benar berskor sekitar
0,28; pada `nomic-embed-text` angka sejenis biasanya 0,6 ke atas. Ambang
mutlak yang pas untuk satu model akan membuang seluruh hasil pada model lain —
dan gagalnya diam-diam: sistem menjawab "informasi tidak ada di dokumen"
padahal dokumennya ada.

Potongan teratas selalu dipertahankan, sehingga penyaringan ini tidak pernah
mengosongkan konteks. Isi `RAG_MIN_SCORE_RATIO=0` untuk mematikannya.

**Konsekuensi.** `POST /chat` menyaring, `POST /query` tidak. Perbedaan itu
disengaja: `/query` adalah endpoint diagnostik, gunanya justru memperlihatkan
apa yang sebenarnya dikembalikan pencarian sebelum disaring.
