/**
 * Layar masuk (PRD §18 - Authentication).
 */
import { useState } from 'react'
import { masuk, simpanToken } from '../services/api'

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

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 px-4">
      <form
        onSubmit={kirim}
        className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h1 className="text-base font-semibold text-slate-800">Agentic RAG Assistant</h1>
        <p className="mt-1 text-sm text-slate-500">Masuk untuk mulai bertanya.</p>

        <label className="mt-5 block text-sm font-medium text-slate-700">
          Nama pengguna
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
        </label>

        <label className="mt-4 block text-sm font-medium text-slate-700">
          Kata sandi
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
        </label>

        {galat && (
          <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800">{galat}</p>
        )}

        <button
          type="submit"
          disabled={sibuk || !username || !password}
          className="mt-5 h-10 w-full rounded-lg bg-indigo-600 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {sibuk ? 'Memeriksa…' : 'Masuk'}
        </button>
      </form>
    </div>
  )
}
