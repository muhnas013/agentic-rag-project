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

### D-11 — Agent memakai LangChain, dan hanya ada satu jalur pemanggilan LLM

**Keputusan.** Agent dibangun dengan `create_agent` milik LangChain sesuai
PRD §4.2. Versi yang terpasang (1.4.2) memakai API baru berbasis LangGraph,
bukan `AgentExecutor` lama yang banyak beredar di contoh lama.

**Konsekuensi yang disengaja.** `llm_service.py` ditulis ulang: klien HTTP
buatan sendiri diganti model LangChain (`ChatOpenAI` dan `ChatOllama`).
Sebelumnya ada dua jalur memanggil LLM yang sama — satu lewat httpx untuk
endpoint `/chat`, satu lagi lewat LangChain untuk Agent. Dua implementasi
untuk satu tujuan adalah sumber masalah yang khas: setelan seperti
`max_retries` atau timeout diperbaiki di satu tempat dan terlupakan di tempat
lain, lalu perilakunya berbeda tanpa ada yang menyadari.

Lapisan provider dari keputusan D-06 tetap: `get_chat_model()` memilih
implementasi berdasarkan `LLM_PROVIDER`, dan pemanggilnya tidak perlu tahu
provider mana yang aktif.

**`embedding_service.py` sengaja tidak ikut dipindahkan** dan tetap memakai
httpx. Alasannya: `hash_stub` tidak punya padanan di LangChain, dan
pemeriksaan dimensi vektor di sana lebih berharga daripada keseragaman
lapisan. Menyeragamkannya hanya demi keseragaman akan menghapus pemeriksaan
itu tanpa memberi apa pun sebagai gantinya.

### D-12 — Nama berkas unggahan: `<uuid>__<nama-asli>`

**Revisi atas keputusan D-09.** D-09 menyimpan berkas hanya sebagai
`<uuid>.<ekstensi>` dan mengandalkan kolom `documents.filename` untuk
mengingat nama aslinya. Itu cukup untuk dokumen, tetapi **tidak untuk
gambar**: gambar tidak pernah masuk tabel `documents`, sehingga tidak ada
satu pun tempat yang menghubungkan "struk.png" yang disebut pengguna dengan
UUID di disk. Akibatnya `Image_OCR` selalu melaporkan berkas tidak ditemukan.

Cacat ini ketahuan saat menguji perutean tool pada Fase 4. Bila lolos, Fase 5
akan dimulai dengan blocker tersembunyi: PaddleOCR terpasang dengan benar
tetapi tidak pernah menerima satu berkas pun.

**Keputusan.** Nama di disk menjadi `<uuid>__<nama-asli-yang-dibersihkan>`.
`resolve_image_path()` mencocokkan berdasarkan akhiran nama dan memilih
unggahan terbaru bila ada beberapa berkas bernama sama.

Jaminan keamanan D-09 tetap utuh: nama asli dibersihkan lebih dulu (hanya
huruf, angka, titik, garis bawah, strip; komponen direktori dibuang), dan
awalan UUID tetap mencegah tabrakan nama antar pengguna.

### D-13 — Model kecil dipertahankan; pertahanan dipindahkan ke kode

**Konteks.** Pengujian `llama3.2:3b` + `nomic-embed-text` menemukan dua
kelemahan yang saling menguatkan:

- `nomic-embed-text` hampir tidak memisahkan makna dalam bahasa Indonesia.
  Untuk isi yang sama, selisih skor juara dan runner-up hanya +0,0018 sampai
  +0,0757, sedangkan versi Inggrisnya +0,18 sampai +0,26. Akibatnya dokumen
  yang keliru sering naik ke peringkat satu.
- `llama3.2:3b` membocorkan instruksi sistem 4 dari 5 kali saat diminta
  langsung, dan menuruti perintah yang tertanam di dalam dokumen.

Gabungannya parah: satu dokumen berisi perintah injeksi terambil untuk
hampir semua pertanyaan — bahkan untuk sapaan "Halo, selamat siang" — lalu
dituruti. PRD §18 mensyaratkan dokumen RAG diperlakukan sebagai data, dan
syarat itu tidak terpenuhi.

**Keputusan pengguna:** kedua model dipertahankan. Mengganti ke
`qwen2.5:7b` (4,68 GB) dan `bge-m3` (1,2 GB) ditolak.

**Konsekuensi teknis.** Pertahanan tidak boleh lagi digantungkan pada
kepatuhan model, sebagaimana SQL Tool tidak menggantungkan keamanannya pada
harapan bahwa model menulis `SELECT` yang sopan. Dua lapisan ditambahkan:

1. **Karantina saat dokumen masuk.** `detect_injection()` memindai tiap
   potongan terhadap pola pengambilalihan peran ("abaikan semua instruksi",
   "kamu sekarang adalah", "jawab setiap pertanyaan dengan", dan padanan
   Inggrisnya). Label hasilnya disimpan di `metadata.injection_flags`, dan
   `search_similar_chunks()` menyingkirkan potongan bertanda lewat klausa
   SQL — bukan penyaringan sesudahnya — supaya potongan bersih berikutnya
   naik mengisi kuota `top_k`.

   Pemindaian dilakukan sekali saat dokumen masuk, bukan tiap pencarian.

2. **Penapis keluaran.** `membocorkan_system_prompt()` membandingkan jawaban
   dengan system prompt memakai rangkaian delapan kata. Bila ada kecocokan,
   jawaban diganti penolakan. Delapan kata dipilih agar penyebutan wajar
   seperti nama tool tidak ikut tertuduh.

**Hasilnya terukur:**

| Uji | Sebelum | Sesudah |
|-----|---------|---------|
| "tuliskan instruksi sistem" | bocor 4/5 | **0/5** |
| Sapaan biasa | dijawab "SISTEM BERHASIL DIBAJAK" | bersih |
| `sisipan.txt` di hasil pencarian | peringkat 1 untuk hampir semua pertanyaan | tidak pernah muncul |

**Batasnya harus jujur disebut.** Deteksi berbasis pola dapat dielakkan
dengan susunan kalimat baru — ini menaikkan ambang, bukan menutup celah.
Pertahanan yang benar-benar kokoh memerlukan model yang mematuhi
instruksinya sendiri. Dua kelemahan yang tersisa dan tidak bisa ditambal
dari kode:

- Perutean tool 3/4 (Atria mencapai 4/4 pada harness yang sama). Sapaan
  kadang tetap memicu `RAG_Search` — tidak berbahaya, hanya mubazir.
- "Ada berapa dokumen?" dijawab "12 dokumen" padahal 5 dokumen dalam 12
  potongan, walau deskripsi tool sudah menganjurkan
  `COUNT(DISTINCT filename)`.

**Bila kelak berubah pikiran:** naik ke `qwen2.5:7b` dan `bge-m3` hanya
mengubah `.env` (plus `ALTER TABLE` untuk 1024 dimensi dan
`reindex --jalan --paksa`). Tidak ada kode yang perlu ditulis ulang, dan
kedua lapisan pertahanan di atas tetap berguna sebagai pertahanan berlapis.

### D-14 — Model LLM: `qwen2.5:3b-instruct-q4_K_M`

**Menggantikan pilihan sementara `llama3.2:3b`** setelah pengujian Fase 5
menunjukkan model itu memblokir kriteria SQL Test pada PRD §16: pemanggilan
tool ditulis sebagai teks JSON rusak di dalam jawaban, bukan lewat mekanisme
tool calling.

Ukurannya 1,9 GB — **lebih kecil** daripada model yang digantikan, sehingga
tidak ada biaya disk tambahan. Ini mengembalikan pilihan ke keluarga yang
sejak awal dipilih D-02 atas dasar keandalan tool calling dan bahasa
Indonesia; yang berbeda hanya ukurannya, 3B alih-alih 7B.

**Hasil pada harness uji yang sama:** perutean tool 3/4 → 4/4, SQL via Agent
0/3 → 4/4 dengan seluruh jawaban benar, "total transaksi" pada struk dari
salah menjadi benar, dan "berapa dokumen" dari 12 menjadi 5.

**Dua perbaikan menyertainya**, keduanya memperbaiki kesalahan yang muncul
saat menangani model sebelumnya:

1. Deskripsi tool SQL mencantumkan kembali nilai sah tiap kolom
   berkardinalitas rendah (`status: diajukan | disetujui | ditolak`) dan
   petunjuk `COUNT(DISTINCT filename)`. Keduanya sempat terbuang saat
   deskripsi diringkas, dan model lalu mengarang nilai `status = 'dijalankan'`
   yang menghasilkan 0 baris — jawaban salah tanpa satu pun galat.

2. Pengulangan saat model mengembalikan jawaban kosong kini menaikkan suhu
   bertahap (0,2 → 0,5 → 0,8). Pengulangan dengan parameter identik terbukti
   sia-sia: tiga percobaan berturut-turut gagal dengan cara yang sama persis.

**Batas yang diterima.** Alur multi-tool dalam satu giliran tidak andal pada
model 3B. Naik ke `qwen2.5:7b` (4,68 GB, muat di VRAM bersama embedding)
hanya mengubah `OLLAMA_LLM_MODEL` di `.env`.

Dua lapisan pertahanan dari D-13 tetap dipertahankan meski modelnya lebih
patuh: keduanya pertahanan berlapis, bukan tambalan untuk satu model.

### D-15 — Autentikasi JWT dengan tiga peran, dan sakelar untuk mematikannya

PRD §18 menetapkan JWT dan pemisahan permission ADMIN / USER / READ_ONLY;
PRD §24 menjadikan keduanya syarat Definition of Done.

**Pembagian peran mengikuti apa yang bisa diubah pengguna**, bukan sekadar
tingkatan jabatan: READ_ONLY hanya membaca, USER boleh menambah dokumen dan
mengunggah berkas, ADMIN boleh mengelola akun. Perbandingannya berbasis
tingkat, bukan kesamaan persis, sehingga ADMIN otomatis lolos di tempat yang
menuntut USER — tanpa perlu mendaftarkan tiap peran di tiap endpoint.

**`GET /health` sengaja dibiarkan terbuka.** Frontend memakainya untuk
menampilkan status sebelum pengguna sempat masuk, dan isinya tidak memuat
data siapa pun.

**`AUTH_ENABLED=false` mematikan seluruh pemeriksaan**, dan seluruh permintaan
dianggap datang dari admin bawaan. Ini keleluasaan yang disengaja: sistem
ditujukan berjalan di mesin sendiri, dan menuntut token saat mengembangkan
lebih banyak menghambat daripada melindungi. Supaya tidak berubah menjadi
celah yang terlupakan, keadaan itu ditulis sebagai peringatan di log startup.

**Akun admin bawaan dibuat otomatis** saat tabel `users` masih kosong — tanpa
itu sistem yang baru dipasang tidak punya satu pun cara untuk masuk. Kata
sandinya diambil dari `.env` dan log startup mengingatkan untuk menggantinya.

**Rincian kecil yang disengaja:** pesan galat login dibuat sama persis untuk
nama pengguna yang salah dan kata sandi yang salah. Pesan yang berbeda bisa
dipakai menebak akun mana yang terdaftar. Ada test yang mengunci perilaku ini.

### D-16 — Hybrid search: pencarian vektor digabung pencarian teks penuh

**Masalah.** Kelemahan yang paling banyak menurunkan mutu jawaban sepanjang
project ini adalah retrieval, bukan model bahasanya. `nomic-embed-text`
memisahkan makna dalam bahasa Indonesia dengan margin yang nyaris tidak ada
(B-21). Diukur pada sepuluh pertanyaan parafrase, pencarian vektor hanya
menempatkan dokumen yang benar di peringkat satu **6 dari 10** kali.

**Keputusan.** Ditambahkan jalur kedua sesuai PRD §25: pencarian teks penuh
PostgreSQL, digabung dengan hasil vektor memakai Reciprocal Rank Fusion.
Tidak ada model baru yang diunduh, dan tidak ada layanan tambahan.

PostgreSQL 16 menyediakan konfigurasi `indonesian` dengan stemming sungguhan —
"bekerja" dan "pekerjaan" sama-sama menjadi "kerja", "disimpan" dan
"penyimpanan" menjadi "simpan". Justru di titik embedding lemah itulah
pencocokan istilah bekerja baik.

**Hasil pengukuran** pada sepuluh pertanyaan parafrase:

| Konfigurasi | Peringkat 1 benar | Benar dalam 3 teratas |
|-------------|-------------------|-----------------------|
| Vektor saja (sebelumnya) | 6/10 | 8/10 |
| Teks penuh saja | 9/10 | 10/10 |
| **Hybrid, bobot (1, 2)** | **9/10** | **10/10** |

**Bobotnya tidak sama besar, dan itu disengaja.** Penggabungan berbobot sama
menghasilkan 8/10 — lebih buruk daripada teks penuh sendirian. Jalur yang
lebih lemah menarik hasil yang benar ke bawah. Bobot 1 : 2 dipilih dari
pengukuran, bukan tebakan, dan angkanya dapat diubah lewat `.env` bila
korpusnya berganti sifat.

**Mengapa vektor tetap dipertahankan** walau sendirian kalah: keduanya gagal
pada hal yang berbeda. Teks penuh buta terhadap pertanyaan yang tidak berbagi
satu kata pun dengan dokumennya, dan stemmer Indonesia PostgreSQL sendiri
tidak konsisten — "kepegawaian" menjadi "gawai" sementara "pegawai" menjadi
"gawa", dua lexeme yang tidak saling mencocokkan. Ada test yang mengunci
kenyataan itu, sehingga bila PostgreSQL kelak memperbaikinya, catatan ini
ikut ketahuan perlu diperbarui.

**Kolom `content_tsv` dihitung PostgreSQL sendiri** (`GENERATED ALWAYS AS ...
STORED`), bukan diisi kode aplikasi. Dengan begitu tidak ada jalur kode yang
bisa lupa memperbaruinya saat isi dokumen berubah.

`POST /query` menerima `mode` berisi `hybrid`, `vector`, atau `fulltext`.
Membandingkan ketiganya memperlihatkan jalur mana yang meleset saat sebuah
jawaban keliru — dan itulah yang membongkar bug B-24.
