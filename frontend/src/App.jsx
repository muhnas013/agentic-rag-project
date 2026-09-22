/**
 * Kerangka halaman: layar masuk, atau header status + antarmuka percakapan.
 */
import { useCallback, useEffect, useState } from 'react'
import ChatBox from './components/ChatBox'
import LoginForm from './components/LoginForm'
import {
  akunSaya,
  ambilKesehatan,
  ambilToken,
  hapusToken,
  pasangPenangananSesiBerakhir,
} from './services/api'

function IndikatorStatus() {
  const [status, setStatus] = useState(null)
  const [galat, setGalat] = useState(null)

  useEffect(() => {
    ambilKesehatan().then(setStatus).catch((e) => setGalat(e.message))
  }, [])

  if (galat) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-rose-600">
        <span className="h-2 w-2 rounded-full bg-rose-500" />
        Backend tidak terhubung
      </span>
    )
  }

  if (!status) return <span className="text-xs text-slate-400">Memeriksa…</span>

  return (
    <span
      className="flex items-center gap-1.5 text-xs text-slate-500"
      title={`LLM ${status.llm_model} · embedding ${status.embedding_model} (${status.embedding_dim} dimensi)`}
    >
      <span
        className={`h-2 w-2 rounded-full ${status.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500'}`}
      />
      {status.llm_model}
    </span>
  )
}

export default function App() {
  const [akun, setAkun] = useState(null)
  const [memeriksa, setMemeriksa] = useState(true)

  const keluar = useCallback(() => {
    hapusToken()
    setAkun(null)
  }, [])

  // Token yang ditolak backend membuat App kembali ke layar masuk, alih-alih
  // membiarkan setiap permintaan berikutnya gagal satu per satu.
  useEffect(() => {
    pasangPenangananSesiBerakhir(() => setAkun(null))
  }, [])

  // Token tersimpan diperiksa ke backend: bisa saja sudah kedaluwarsa.
  useEffect(() => {
    if (!ambilToken()) {
      setMemeriksa(false)
      return
    }
    akunSaya()
      .then((u) => setAkun({ username: u.username, role: u.role }))
      .catch(() => hapusToken())
      .finally(() => setMemeriksa(false))
  }, [])

  if (memeriksa) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50 text-sm text-slate-400">
        Memeriksa sesi…
      </div>
    )
  }

  if (!akun) return <LoginForm onBerhasil={setAkun} />

  return (
    <div className="flex h-full flex-col bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
          <h1 className="text-sm font-semibold text-slate-800">Agentic RAG Assistant</h1>
          <div className="flex items-center gap-4">
            <IndikatorStatus />
            <span className="hidden text-xs text-slate-500 sm:inline">
              {akun.username}
              <span className="ml-1.5 rounded-full bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
                {akun.role}
              </span>
            </span>
            <button
              onClick={keluar}
              className="text-xs text-slate-500 underline-offset-2 transition hover:text-slate-800 hover:underline"
            >
              Keluar
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 overflow-hidden">
        {/* Peran diteruskan supaya tombol unggah disembunyikan bagi READ_ONLY,
            yang memang akan ditolak backend dengan 403. */}
        <ChatBox peran={akun.role} />
      </main>
    </div>
  )
}
