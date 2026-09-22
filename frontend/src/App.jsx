/**
 * Kerangka halaman: layar masuk, atau header status + antarmuka percakapan.
 *
 * Header membentang selebar jendela dan bagian kirinya selebar sidebar,
 * sehingga garis batas keduanya bertemu. Sebelumnya isi header dibatasi
 * `max-w-3xl` sendiri, dan hasilnya judul maupun tombol mengambang tidak
 * sejajar dengan apa pun di bawahnya.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import ChatBox from './components/ChatBox'
import Merek from './components/Merek'
import PanelDokumen from './components/PanelDokumen'
import Sidebar from './components/Sidebar'
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

  const dasar =
    'flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition'

  if (galat) {
    return (
      <span className={`${dasar} border-rose-200 bg-rose-50 text-rose-700`}>
        <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
        Backend terputus
      </span>
    )
  }

  if (!status) {
    return (
      <span className={`${dasar} border-slate-200 bg-slate-50 text-slate-400`}>
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-300" />
        Memeriksa…
      </span>
    )
  }

  const sehat = status.status === 'ok'
  return (
    <span
      className={`${dasar} ${
        sehat
          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
          : 'border-amber-200 bg-amber-50 text-amber-800'
      }`}
      title={`LLM ${status.llm_model} · embedding ${status.embedding_model} (${status.embedding_dim} dimensi)`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${sehat ? 'bg-emerald-500' : 'bg-amber-500'}`}
      />
      <span className="hidden font-medium md:inline">{status.llm_model}</span>
      <span className="font-medium md:hidden">Siap</span>
    </span>
  )
}

const KUNCI_SESI = 'agentic-rag-session'

const sesiBaru = () => `sesi-${crypto.randomUUID().slice(0, 8)}`

/** Sesi terakhir diingat, supaya memuat ulang halaman tidak kehilangan tempat. */
function sesiTersimpan() {
  let id = localStorage.getItem(KUNCI_SESI)
  if (!id) {
    id = sesiBaru()
    localStorage.setItem(KUNCI_SESI, id)
  }
  return id
}

export default function App() {
  const [akun, setAkun] = useState(null)
  const [memeriksa, setMemeriksa] = useState(true)
  const [sessionId, setSessionId] = useState(sesiTersimpan)
  // Berubah setiap kali ada pesan baru, memicu sidebar menyegarkan daftarnya.
  const [penanda, setPenanda] = useState(0)
  const [dokumenTerbuka, setDokumenTerbuka] = useState(false)
  // Dinaikkan setiap unggahan berhasil, supaya daftar berkas ikut berubah
  // tanpa perlu ditutup lalu dibuka lagi.
  const [penandaDokumen, setPenandaDokumen] = useState(0)

  // Memilih berkas menyiapkan awal pertanyaannya di kolom masukan. Dilakukan
  // lewat ref, bukan prop: ini satu kejadian sesaat, bukan keadaan yang perlu
  // diingat — dan memilih berkas yang sama dua kali harus tetap bekerja.
  const chatRef = useRef(null)

  const pilihBerkas = useCallback((berkas) => {
    chatRef.current?.siapkanPertanyaan(
      berkas.jenis === 'gambar'
        ? `Apa isi gambar ${berkas.filename}? `
        : `Menurut dokumen ${berkas.filename}, `,
    )
    setDokumenTerbuka(false)
  }, [])

  const pindahSesi = useCallback((id) => {
    setSessionId(id)
    localStorage.setItem(KUNCI_SESI, id)
  }, [])

  const mulaiBaru = useCallback(() => {
    pindahSesi(sesiBaru())
    setPenanda((n) => n + 1)
  }, [pindahSesi])

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
      <div className="flex h-full flex-col items-center justify-center gap-3 bg-slate-50 text-sm text-slate-400">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-merek-500" />
        Memeriksa sesi…
      </div>
    )
  }

  if (!akun) return <LoginForm onBerhasil={setAkun} />

  return (
    <div className="flex h-full flex-col bg-slate-50">
      <header className="z-20 flex h-14 shrink-0 items-center border-b border-slate-200 bg-white/85 backdrop-blur">
        {/* Selebar sidebar, sehingga garis pemisahnya menyambung ke bawah. */}
        <div className="hidden h-full w-64 shrink-0 items-center border-r border-slate-200 px-4 sm:flex">
          <Merek />
        </div>

        <div className="flex min-w-0 flex-1 items-center justify-between gap-3 px-4 sm:px-6">
          <div className="sm:hidden">
            <Merek />
          </div>

          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <IndikatorStatus />

            <button
              onClick={() => setDokumenTerbuka(true)}
              className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:border-merek-200 hover:bg-merek-50 hover:text-merek-700"
            >
              <span aria-hidden>🗂</span>
              <span className="hidden sm:inline">Dokumen</span>
            </button>

            <div className="hidden items-center gap-2 border-l border-slate-200 pl-3 sm:flex">
              <span className="text-xs font-medium text-slate-600">
                {akun.username}
              </span>
              <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                {akun.role}
              </span>
            </div>

            <button
              onClick={keluar}
              title="Keluar"
              className="rounded-full border border-transparent px-2.5 py-1 text-xs text-slate-500 transition hover:border-slate-200 hover:bg-slate-50 hover:text-slate-800"
            >
              Keluar
            </button>
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Sidebar disembunyikan pada layar sempit; percakapan tetap bisa
            dipakai, hanya daftarnya yang tidak muat ditampilkan. */}
        <div className="hidden sm:flex">
          <Sidebar
            sessionId={sessionId}
            onPilih={pindahSesi}
            onBaru={mulaiBaru}
            penanda={penanda}
            bolehHapus={akun.role !== 'READ_ONLY'}
          />
        </div>

        {/* Lebar bacaan dibatasi di dalam ChatBox, bukan di sini: bilah
            masukan harus membentang penuh agar tidak tampak mengambang
            terpisah dari percakapannya. */}
        <main className="flex min-w-0 flex-1 flex-col">
          {/* Peran diteruskan supaya tombol unggah disembunyikan bagi READ_ONLY,
              yang memang akan ditolak backend dengan 403. */}
          <ChatBox
            ref={chatRef}
            peran={akun.role}
            sessionId={sessionId}
            onPesanBaru={() => setPenanda((n) => n + 1)}
            onUnggah={() => setPenandaDokumen((n) => n + 1)}
          />
        </main>
      </div>

      {/* Dirender hanya saat terbuka, sehingga daftarnya selalu dimuat ulang
          dan tidak menyimpan keadaan basi dari pembukaan sebelumnya. */}
      {dokumenTerbuka && (
        <PanelDokumen
          onTutup={() => setDokumenTerbuka(false)}
          onPilih={pilihBerkas}
          penanda={penandaDokumen}
        />
      )}
    </div>
  )
}
