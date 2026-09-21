# Checklist Progres Pengerjaan Project Agentic RAG

## Status umum
- [ ] Project mulai didefinisikan
- [ ] PRD dibaca dan dipahami
- [ ] Roadmap kerja dibuat
- [ ] Infrastruktur dasar disiapkan
- [ ] Backend utama berjalan
- [ ] RAG minimal berfungsi
- [ ] Integrasi Ollama selesai
- [ ] Integrasi PostgreSQL + pgvector selesai
- [ ] OCR tool selesai
- [ ] SQL tool selesai
- [ ] Frontend chat basic selesai
- [ ] Agent orchestrator dasar selesai
- [ ] Pengujian end-to-end dilakukan
- [ ] Dokumentasi teknis dibuat
- [ ] Project siap demo / presentasi

## Fase 1: Persiapan & Foundation
- [ ] Review PRD dan scope project
- [ ] Tentukan teknologi yang dipakai
- [ ] Siapkan struktur folder project
- [ ] Buat file environment/config dasar
- [ ] Siapkan repository dan dokumentasi awal

## Fase 2: Backend Core
- [ ] Setup FastAPI project
- [ ] Konfigurasi CORS dan routing dasar
- [ ] Setup PostgreSQL database
- [ ] Setup pgvector extension
- [ ] Buat model tabel chat history
- [ ] Buat model tabel dokumen / embedding
- [ ] Buat service upload dokumen
- [ ] Buat proses embedding dokumen
- [ ] Buat endpoint query RAG
- [ ] Uji retrieval basic

## Fase 3: Integrasi LLM Lokal
- [ ] Setup Ollama
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
