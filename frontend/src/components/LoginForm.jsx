/**
 * Layar masuk (PRD §18 - Authentication).
 */
import { useState } from 'react'
import { masuk, simpanToken } from '../services/api'
import { IkonPeringatan } from './Ikon'
import Merek from './Merek'

export default function LoginForm({ onBerhasil }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [galat, setGalat] = useState(null)
  const [sibuk, setSibuk] = useState(false)

  async function kirim(e) {
    e.preventDefault()
    setGalat(null)
    setSibuk(true)
    try {
      const hasil = await masuk({ username, password })
      simpanToken(hasil.access_token)
      onBerhasil({ username: hasil.username, role: hasil.role })
    } catch (error) {
      setGalat(error.message)
    } finally {
      setSibuk(false)
    }
  }

  const kolom =
    'mt-1.5 h-11 w-full rounded-xl border border-garis bg-naik px-3.5 text-sm text-terang outline-none transition placeholder:text-redup focus:border-garis2'

  return (
    <div className="relative flex h-full items-center justify-center overflow-hidden bg-dasar px-4">
      {/* Dua kabut warna yang sangat samar. Tanpa ini latar hitam polos
          membuat kartu masuk tampak mengambang tanpa tempat. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-24 -top-24 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-32 -right-24 h-96 w-96 rounded-full bg-teal-500/10 blur-3xl"
      />

      <form
        onSubmit={kirim}
        className="animate-naik relative w-full max-w-sm rounded-2xl border border-garis bg-panel p-7 shadow-2xl shadow-black/40"
      >
        <Merek ukuran="besar" keterangan="Asisten dokumen & data" />

        <p className="mt-5 text-sm text-redup">Masuk untuk mulai bertanya.</p>

        <label className="mt-5 block text-sm font-medium text-sedang">
          Nama pengguna
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
            placeholder="admin"
            className={kolom}
          />
        </label>

        <label className="mt-4 block text-sm font-medium text-sedang">
          Kata sandi
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            placeholder="••••••"
            className={kolom}
          />
        </label>

        {galat && (
          <p className="mt-4 flex items-start gap-2 rounded-xl border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-sm text-rose-200">
            <IkonPeringatan ukuran={16} className="mt-0.5" />
            <span>{galat}</span>
          </p>
        )}

        <button
          type="submit"
          disabled={sibuk || !username || !password}
          className="mt-6 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-terang text-sm font-medium text-dasar transition hover:opacity-90 disabled:cursor-not-allowed disabled:bg-naik disabled:text-redup"
        >
          {sibuk && (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-dasar/30 border-t-dasar" />
          )}
          {sibuk ? 'Memeriksa…' : 'Masuk'}
        </button>

        <p className="mt-5 text-center text-[11px] leading-relaxed text-redup">
          Semua model berjalan lokal di mesin ini. Dokumen dan pertanyaan
          tidak dikirim ke layanan luar.
        </p>
      </form>
    </div>
  )
}
