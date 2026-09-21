/**
 * Kerangka halaman: header status + antarmuka percakapan.
 */
import { useEffect, useState } from 'react'
import ChatBox from './components/ChatBox'
import { ambilKesehatan } from './services/api'

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

  const sehat = status.status === 'ok'
  return (
    <span
      className="flex items-center gap-1.5 text-xs text-slate-500"
      title={`LLM ${status.llm_model} · embedding ${status.embedding_model} (${status.embedding_dim} dimensi)`}
    >
      <span
        className={`h-2 w-2 rounded-full ${sehat ? 'bg-emerald-500' : 'bg-amber-500'}`}
      />
      {status.llm_model}
    </span>
  )
}

export default function App() {
  return (
    <div className="flex h-full flex-col bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <h1 className="text-sm font-semibold text-slate-800">
            Agentic RAG Assistant
          </h1>
          <IndikatorStatus />
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 overflow-hidden">
        <ChatBox />
      </main>
    </div>
  )
}
