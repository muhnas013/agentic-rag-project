/**
 * Kerangka halaman: layar masuk, atau header status + antarmuka percakapan.
 *
 * Header membentang selebar jendela dan bagian kirinya selebar sidebar,
 * sehingga garis batas keduanya bertemu. Sebelumnya isi header dibatasi
 * `max-w-3xl` sendiri, dan hasilnya judul maupun tombol mengambang tidak
 * sejajar dengan apa pun di bawahnya.
 *
 * Susunan kanan atas mengikuti pola Grok: satu perintah berikon, satu
 * tombol ikon saja, lalu dua pil — satu bergaris, satu terisi putih.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import ChatBox from './components/ChatBox'
import { IkonDokumen, IkonKeluar, IkonRoda } from './components/Ikon'
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

/**
 * Tombol roda gigi: keadaan sistem, ditampilkan saat diminta.
 *
 * Sebelumnya nama model tampil terus-menerus sebagai lencana, dan rinciannya
 * hanya muncul sebagai tooltip — yang tidak pernah ditemukan orang. Di balik
 * roda gigi, keterangannya justru lebih lengkap dan headernya jauh lebih
 * lengang. Titik kecil pada rodanya tetap memberi tahu bila ada yang salah,
 * sehingga menyembunyikan rinciannya tidak berarti menyembunyikan masalah.
 */
function TombolStatus() {
  const [status, setStatus] = useState(null)
  const [galat, setGalat] = useState(null)
  const [buka, setBuka] = useState(false)
  const wadahRef = useRef(null)

  useEffect(() => {
    ambilKesehatan().then(setStatus).catch((e) => setGalat(e.message))
  }, [])

  useEffect(() => {
    if (!buka) return
    const tutup = (e) => {
      if (e.key === 'Escape') setBuka(false)
    }
    const klikLuar = (e) => {
      if (!wadahRef.current?.contains(e.target)) setBuka(false)
    }
    window.addEventListener('keydown', tutup)
    document.addEventListener('mousedown', klikLuar)
    return () => {
      window.removeEventListener('keydown', tutup)
      document.removeEventListener('mousedown', klikLuar)
    }
  }, [buka])

  const sehat = status?.status === 'ok'
  const warnaTitik = galat
    ? 'bg-rose-500'
    : !status
      ? 'bg-garis2'
      : sehat
        ? 'bg-emerald-500'
        : 'bg-amber-500'

  const baris = [
    ['Backend', galat ? 'terputus' : status ? status.status : 'memeriksa…'],
    ['Model LLM', status?.llm_model],
    ['Embedding', status?.embedding_model],
    ['Dimensi vektor', status?.embedding_dim],
    ['Database', status ? (status.database ? 'terhubung' : 'gagal') : null],
    ['Extension vector', status ? (status.vector_extension ? 'aktif' : 'tidak ada') : null],
  ].filter(([, nilai]) => nilai !== null && nilai !== undefined)

  return (
    <div ref={wadahRef} className="relative">
      <button
        onClick={() => setBuka((b) => !b)}
        title="Keadaan sistem"
        aria-label="Keadaan sistem"
        aria-expanded={buka}
        className="relative flex h-8 w-8 items-center justify-center rounded-full text-sedang transition hover:bg-naik hover:text-terang"
      >
        <IkonRoda ukuran={17} />
        <span
          className={`absolute right-1 top-1 h-1.5 w-1.5 rounded-full ring-2 ring-panel ${warnaTitik}`}
        />
      </button>

      {buka && (
        <div className="animate-naik absolute right-0 top-10 z-30 w-64 rounded-xl border border-garis bg-panel p-3 shadow-2xl shadow-black/50">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-redup">
            Keadaan sistem
          </p>
          {galat && <p className="text-xs text-rose-400">{galat}</p>}
          <dl className="space-y-1.5">
            {baris.map(([label, nilai]) => (
              <div key={label} className="flex items-baseline justify-between gap-3">
                <dt className="shrink-0 text-xs text-redup">{label}</dt>
                <dd className="truncate text-right text-xs text-terang">{nilai}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-2.5 border-t border-garis pt-2 text-[11px] leading-relaxed text-redup">
            Semua model berjalan lokal di mesin ini.
          </p>
        </div>
      )}
    </div>
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
      <div className="flex h-full flex-col items-center justify-center gap-3 bg-dasar text-sm text-redup">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-garis border-t-sedang" />
        Memeriksa sesi…
      </div>
    )
  }

  if (!akun) return <LoginForm onBerhasil={setAkun} />

  return (
    <div className="flex h-full flex-col bg-dasar">
      <header className="z-20 flex h-14 shrink-0 items-center border-b border-garis bg-panel">
        {/* Selebar sidebar, sehingga garis pemisahnya menyambung ke bawah. */}
        <div className="hidden h-full w-64 shrink-0 items-center border-r border-garis px-4 sm:flex">
          <Merek />
        </div>

        <div className="flex min-w-0 flex-1 items-center justify-between gap-3 px-3 sm:px-5">
          <div className="sm:hidden">
            <Merek />
          </div>

          <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
            <button
              onClick={() => setDokumenTerbuka(true)}
              className="flex items-center gap-2 rounded-full px-2.5 py-1.5 text-sm font-medium text-sedang transition hover:bg-naik hover:text-terang"
            >
              <IkonDokumen ukuran={17} />
              <span className="hidden sm:inline">Dokumen</span>
            </button>

            <TombolStatus />

            {/* Dua pil: identitas bergaris, lalu keluar terisi putih — bentuk
                yang sama dengan pasangan tombol akun pada Grok. Yang terisi
                dipakai untuk "Keluar" karena itu satu-satunya tindakan di
                sini; identitas hanya keterangan, jadi tetap bergaris. */}
            <span className="hidden items-center gap-1.5 rounded-full border border-garis px-3 py-1.5 text-sm text-sedang sm:flex">
              {akun.username}
              <span className="text-[10px] font-medium uppercase tracking-wide text-redup">
                {akun.role}
              </span>
            </span>

            <button
              onClick={keluar}
              title="Keluar"
              className="flex items-center gap-1.5 rounded-full bg-terang px-3.5 py-1.5 text-sm font-medium text-dasar transition hover:opacity-90"
            >
              <IkonKeluar ukuran={15} className="sm:hidden" />
              <span className="hidden sm:inline">Keluar</span>
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
