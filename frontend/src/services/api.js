/**
 * Klien HTTP ke backend FastAPI (PRD §4.1 dan §20).
 *
 * Seluruh pemanggilan API lewat berkas ini supaya komponen tidak perlu tahu
 * alamat backend maupun bentuk galatnya.
 */
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const KUNCI_TOKEN = 'agentic-rag-token'

export const ambilToken = () => localStorage.getItem(KUNCI_TOKEN)
export const simpanToken = (token) => localStorage.setItem(KUNCI_TOKEN, token)
export const hapusToken = () => localStorage.removeItem(KUNCI_TOKEN)

const http = axios.create({
  baseURL: BASE_URL,
  // Agent bisa memanggil beberapa tool berurutan, dan OCR pada pemanggilan
  // pertama memuat model ke memori. Batas bawaan Axios terlalu pendek.
  timeout: 180000,
  headers: { 'Content-Type': 'application/json' },
})

// Token disisipkan di sini, bukan di tiap pemanggilan, supaya tidak ada
// endpoint yang terlewat saat kelak ditambahkan.
http.interceptors.request.use((config) => {
  const token = ambilToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/** Dipanggil saat token ditolak, supaya App bisa menampilkan layar masuk. */
let saatSesiBerakhir = () => {}
export const pasangPenangananSesiBerakhir = (fn) => {
  saatSesiBerakhir = fn
}

/**
 * Ubah galat Axios menjadi pesan yang layak dibaca pengguna.
 *
 * Backend mengirim penjelasan di `detail`; itu yang paling berguna. Bila
 * tidak ada balasan sama sekali, penyebabnya hampir selalu backend belum
 * berjalan — disebutkan langsung supaya tidak ditebak-tebak.
 */
function pesanGalat(error) {
  if (error.response) {
    // Token kedaluwarsa atau tidak sah: bersihkan dan minta masuk lagi,
    // daripada membiarkan seluruh permintaan berikutnya gagal diam-diam.
    if (error.response.status === 401) {
      hapusToken()
      saatSesiBerakhir()
    }
    const detail = error.response.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ')
    return `Backend membalas ${error.response.status}.`
  }
  if (error.code === 'ECONNABORTED') {
    return 'Permintaan melewati batas waktu. Model mungkin sedang memuat, coba lagi.'
  }
  return `Tidak dapat menghubungi backend di ${BASE_URL}. Pastikan sudah berjalan.`
}

export class ApiError extends Error {}

async function panggil(fn) {
  try {
    const { data } = await fn()
    return data
  } catch (error) {
    throw new ApiError(pesanGalat(error))
  }
}

export const masuk = ({ username, password }) =>
  panggil(() => http.post('/auth/login', { username, password }))

export const akunSaya = () => panggil(() => http.get('/auth/me'))

export const kirimPesan = ({ sessionId, pesan }) =>
  panggil(() => http.post('/chat', { session_id: sessionId, message: pesan }))

export const ambilRiwayat = (sessionId) =>
  panggil(() => http.get('/chat/history', { params: { session_id: sessionId } }))

export const daftarSesi = () => panggil(() => http.get('/chat/sessions'))

export const hapusSesi = (sessionId) =>
  panggil(() => http.delete(`/chat/sessions/${sessionId}`))

export const ambilKesehatan = () => panggil(() => http.get('/health'))

export const daftarDokumen = () => panggil(() => http.get('/documents'))

export const unggahBerkas = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return panggil(() =>
    http.post('/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    }),
  )
}

export { BASE_URL }
