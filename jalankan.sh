#!/usr/bin/env bash
#
# Menyalakan seluruh layanan Agentic RAG setelah mesin dihidupkan.
#
# Urutannya tidak sembarang. Ollama diikat ke alamat gateway jaringan Docker
# Compose (lihat OLLAMA_BASE_URL di .env) — alamat itu milik interface yang
# baru dibuat Docker ketika jaringannya naik, bukan milik mesin ini. Karena
# itu Compose harus jalan lebih dulu; bila dibalik, Ollama gagal bind dengan
# "cannot assign requested address" dan penyebabnya tidak terbaca dari pesan
# itu (keputusan D-03).
#
# Aman dijalankan berulang: setiap layanan yang sudah hidup dilewati.
#
#   ./jalankan.sh            nyalakan semuanya
#   ./jalankan.sh --tanpa-ui hanya database, backend, dan Ollama
#
set -euo pipefail

AKAR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$AKAR"

TANPA_UI=0
[[ "${1:-}" == "--tanpa-ui" ]] && TANPA_UI=1

LOG="$AKAR/logs"
mkdir -p "$LOG"

# Warna hanya dipakai bila keluarannya memang ke terminal; bila dialihkan ke
# berkas, kode warnanya cuma jadi sampah yang menyulitkan dibaca.
if [[ -t 1 ]]; then
  H='\033[0;32m'; K='\033[0;31m'; A='\033[0;33m'; R='\033[0;90m'; N='\033[0m'
else
  H=''; K=''; A=''; R=''; N=''
fi

ok()    { echo -e "  ${H}✓${N} $*"; }
gagal() { echo -e "  ${K}✗${N} $*"; }
info()  { echo -e "  ${R}·${N} $*"; }
langkah() { echo -e "\n${A}$*${N}"; }

# --- Setelan dibaca dari .env, bukan ditulis mati di sini ----------------
# Menyalinnya ke skrip berarti dua tempat yang harus diubah bersamaan, dan
# yang satu pasti terlupakan.
if [[ ! -f .env ]]; then
  gagal ".env tidak ada. Salin dari .env.example lebih dulu."
  exit 1
fi

nilai_env() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d '"'"'"'\r'; }

OLLAMA_URL="$(nilai_env OLLAMA_BASE_URL)"
OLLAMA_URL="${OLLAMA_URL:-http://172.28.0.1:11434}"
# http://172.28.0.1:11434 -> 172.28.0.1 dan 11434
OLLAMA_HOSTPORT="${OLLAMA_URL#*://}"
OLLAMA_IP="${OLLAMA_HOSTPORT%%:*}"
OLLAMA_PORT="${OLLAMA_HOSTPORT##*:}"

API_PORT="$(nilai_env API_PORT)"; API_PORT="${API_PORT:-8000}"
UI_PORT=5173   # dipatok strictPort di frontend/vite.config.js

# `lepas <perintah...> <berkas-log>` — jalankan sebagai proses lepas.
#
# Memakai `setsid`, bukan `nohup ... & disown`. Yang kedua terlihat benar
# tetapi tidak cukup: prosesnya tetap menjadi anak skrip ini, sehingga
# skripnya menunggu proses itu selesai dan tidak pernah kembali ke prompt.
# Terbukti saat diuji — skrip menggantung hampir sembilan menit sampai
# dihentikan paksa. `setsid` memindahkannya ke sesi sendiri, dan stdin
# dialihkan dari /dev/null supaya ia tidak menunggu ketikan.
lepas() {
  local log="${*: -1}"
  local perintah=("${@:1:$#-1}")
  setsid "${perintah[@]}" >"$log" 2>&1 </dev/null &
}

# `tunggu <detik> <perintah...>` — ulangi sampai berhasil atau waktu habis.
tunggu() {
  local batas=$1; shift
  local mulai=$SECONDS
  until "$@" >/dev/null 2>&1; do
    (( SECONDS - mulai >= batas )) && return 1
    sleep 1
  done
}

# --- 1. Database dan backend ---------------------------------------------
# `docker compose up -d` sekaligus membangunkan daemon Docker lewat
# docker.socket, jadi tidak perlu `systemctl start docker` terpisah.
langkah "1/4  Database dan backend"
if docker compose up -d >"$LOG/compose.log" 2>&1; then
  ok "container dinyalakan"
else
  gagal "docker compose gagal — lihat $LOG/compose.log"
  exit 1
fi

# --- 2. Ollama -------------------------------------------------------------
langkah "2/4  Ollama ($OLLAMA_IP:$OLLAMA_PORT)"
if curl -sf -m 3 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  ok "sudah berjalan"
else
  if ! command -v ollama >/dev/null 2>&1; then
    gagal "perintah 'ollama' tidak ditemukan — lihat docs/menjalankan.md §1"
    exit 1
  fi

  # Alamat gateway baru muncul setelah jaringan Compose naik. Ditunggu di
  # sini supaya kegagalan bind tidak terjadi karena balapan waktu.
  if ! tunggu 20 ip -4 addr show to "$OLLAMA_IP/32"; then
    gagal "alamat $OLLAMA_IP belum ada. Jaringan Compose belum naik?"
    info "periksa: docker network inspect praktek-ai-engineer_default"
    exit 1
  fi

  # `env` diperlukan: setsid menjalankan program, bukan menafsirkan
  # penetapan variabel di depan nama program seperti yang dilakukan shell.
  lepas env OLLAMA_HOST="$OLLAMA_IP:$OLLAMA_PORT" ollama serve "$LOG/ollama.log"

  if tunggu 30 curl -sf -m 2 "$OLLAMA_URL/api/tags"; then
    ok "dinyalakan (log: $LOG/ollama.log)"
  else
    gagal "tidak menyahut dalam 30 detik — lihat $LOG/ollama.log"
    exit 1
  fi
fi

# --- 3. Backend siap melayani ---------------------------------------------
langkah "3/4  Menunggu backend siap"
if tunggu 90 curl -sf -m 3 "http://localhost:$API_PORT/health"; then
  kesehatan="$(curl -s "http://localhost:$API_PORT/health")"
  status="$(echo "$kesehatan" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
  model="$(echo "$kesehatan" | grep -o '"llm_model":"[^"]*"' | cut -d'"' -f4)"
  if [[ "$status" == "ok" ]]; then
    ok "sehat · model $model"
  else
    # Bukan alasan berhenti: /health memang dirancang tetap menjawab saat
    # sebagian bergantungannya bermasalah, justru supaya penyebabnya
    # kelihatan. Keputusannya diserahkan kepada yang membaca.
    gagal "status '$status' — periksa: curl localhost:$API_PORT/health"
  fi
else
  gagal "backend tidak menyahut dalam 90 detik"
  info "lihat: docker compose logs --tail 50 backend"
  exit 1
fi

# --- 4. Frontend -----------------------------------------------------------
if (( TANPA_UI )); then
  langkah "4/4  Frontend dilewati (--tanpa-ui)"
else
  langkah "4/4  Frontend"
  if curl -sf -m 3 "http://localhost:$UI_PORT" >/dev/null 2>&1; then
    ok "sudah berjalan"
  elif [[ ! -d frontend/node_modules ]]; then
    gagal "frontend/node_modules belum ada — jalankan: cd frontend && npm install"
  else
    ( cd frontend && lepas npm run dev "$LOG/frontend.log" )
    if tunggu 30 curl -sf -m 2 "http://localhost:$UI_PORT"; then
      ok "dinyalakan (log: $LOG/frontend.log)"
    else
      gagal "tidak menyahut dalam 30 detik — lihat $LOG/frontend.log"
    fi
  fi
fi

echo
echo -e "${H}Siap.${N}  UI http://localhost:$UI_PORT   API http://localhost:$API_PORT/docs"
echo -e "${R}Menghentikan: docker compose down; pkill -f 'ollama serve'; pkill -f 'vite'${N}"
