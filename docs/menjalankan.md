# Menjalankan dari Mesin Kosong

Langkah lengkap memasang sistem ini di mesin Linux yang belum disiapkan.
Perkiraan waktu: 20 menit, sebagian besar menunggu unduhan (±6,4 GB).

## Prasyarat

| Kebutuhan | Versi | Catatan |
|-----------|-------|---------|
| Docker + Compose | 20.10+ | Backend dan database berjalan di sini |
| Node.js | 18+ | Untuk frontend |
| GPU NVIDIA | 8 GB VRAM | Opsional, tetapi LLM di CPU jauh lebih lambat |
| Disk | ±12 GB | Model 6,4 GB + image Docker |
| RAM | 8 GB tersedia | PaddleOCR di CPU cukup rakus |

Python tidak perlu dipasang di host: backend berjalan di container
`python:3.12-slim` (keputusan D-01).

## 1. Ollama dan model

Ollama berjalan di **host**, bukan di container, supaya mendapat akses GPU
langsung tanpa container toolkit (keputusan D-03).

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Tanpa akses root, tarball resminya bisa diekstrak ke home — runtime CUDA
sudah ikut di dalamnya:

```bash
curl -fL -o /tmp/ollama.tar.zst \
  https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst
mkdir -p ~/.local && tar --zstd -xf /tmp/ollama.tar.zst -C ~/.local
```

Unduh kedua model (±2,3 GB):

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M    # 1,9 GB — LLM Agent
ollama pull nomic-embed-text              # 274 MB — embedding RAG
```

## 2. Jaringan: agar container bisa menjangkau Ollama

Bagian ini paling sering menyita waktu, jadi dijelaskan sebabnya.

Ollama yang mendengarkan di `127.0.0.1` tidak terjangkau dari container.
`host.docker.internal` juga tidak menolong: alamat itu menunjuk bridge
`docker0` yang berbeda dari jaringan Compose, dan aturan isolasi antar-bridge
Docker memblokirnya.

Karena itu Ollama diikat ke **gateway jaringan Compose**, yang subnetnya
sudah dipatok di `docker-compose.yml`:

```bash
OLLAMA_HOST=172.28.0.1:11434 ollama serve
```

Bila host memakai firewall, izinkan subnet itu saja — bukan `0.0.0.0`, yang
akan membuka Ollama bagi siapa pun di jaringan yang sama:

```bash
sudo ufw allow from 172.28.0.0/24 to any port 11434 proto tcp \
  comment 'Ollama untuk container backend'
```

Uji dari dalam container setelah langkah 3:

```bash
docker compose exec backend curl -s -o /dev/null -w "%{http_code}\n" \
  http://172.28.0.1:11434/api/tags      # harus 200
```

## 3. Backend dan database

```bash
git clone <repo> praktek-ai-engineer && cd praktek-ai-engineer
cp .env.example .env
```

Sunting `.env` seperlunya. Minimal yang perlu diganti sebelum dipakai di luar
mesin sendiri:

```
POSTGRES_PASSWORD=...        # kata sandi database
SQL_AGENT_DB_PASSWORD=...    # kata sandi user read-only
JWT_SECRET_KEY=...           # string acak panjang
ADMIN_PASSWORD=...           # kata sandi admin bawaan
```

Lalu:

```bash
docker compose up -d
docker compose logs -f backend      # tunggu "Application startup complete"
curl localhost:8000/health
```

`/health` harus menjawab `"status": "ok"` dengan `database` dan
`vector_extension` bernilai `true`.

Saat pertama dijalankan, tiga hal terjadi otomatis: extension `vector`
diaktifkan, user database read-only dibuat, dan akun admin bawaan dibuat.

## 4. Data sample (opsional, untuk demo)

Skrip data sample ikut berjalan otomatis pada database baru. Untuk database
yang sudah berisi:

```bash
docker exec -i agentic-rag-db psql -U postgres -d agentic_rag \
  < docker/postgres/init/03-sample-data.sql
```

## 5. Frontend

```bash
cd frontend
npm install
npm run dev              # http://localhost:5173
```

Port 5173 harus cocok dengan `CORS_ORIGINS` di `.env` backend. Alamat backend
diatur lewat `frontend/.env` (`VITE_API_BASE_URL`).

## 6. Pemeriksaan akhir

```bash
docker compose exec -w /app backend python -m pytest backend/tests -q
docker compose exec -w /app backend python -m backend.uji_matriks --ulang 1
```

Bila test lulus semua dan matriks memberi 6/7 atau lebih, sistem siap dipakai.

---

## Perintah harian

```bash
docker compose logs -f backend                    # ikuti log
docker compose up -d backend                      # muat ulang setelah .env berubah
docker compose down                               # berhenti, data tetap ada
docker compose down -v                            # berhenti dan HAPUS database
docker compose build backend                      # setelah requirements.txt berubah
```

Kode di `./backend` di-mount sebagai volume, jadi perubahan kode langsung
dimuat ulang tanpa build ulang.

## Hal yang mudah terlewat

**`docker compose restart` tidak membaca ulang `.env`.** Environment dibekukan
saat container dibuat. Gejalanya membingungkan: berkasnya jelas sudah benar,
tetapi aplikasi bersikeras nilainya kosong. Pakai `up -d`.

**Skrip di `docker/postgres/init/` hanya jalan sekali**, yaitu saat volume
database masih kosong. Mengubahnya tidak berpengaruh pada database yang sudah
ada kecuali dijalankan manual, atau setelah `docker compose down -v` — yang
juga menghapus seluruh data.

**Subnet Compose dipatok `172.28.0.0/24`** dan tidak boleh diubah sembarangan:
aturan firewall yang mengizinkan container menjangkau Ollama mengacu ke subnet
itu. Alamat yang bergeser memutus sambungan tanpa pesan galat yang menjelaskan.

**Model baru memuat ke VRAM saat pertama dipakai** (±1,5 menit), dan model OCR
ke memori (±6 detik). Panaskan sebelum demo dengan menjalankan matriks uji.
