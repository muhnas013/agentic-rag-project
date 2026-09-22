/**
 * Daftar berkas yang sudah diunggah (PRD §15).
 *
 * Dibuat sebagai panel yang dibuka dari header, bukan bagian tetap sidebar:
 * sidebar sudah dipakai riwayat percakapan dan disembunyikan pada layar
 * sempit, sedangkan daftar dokumen justru perlu tetap terjangkau di sana.
 */
import { useEffect, useState } from 'react'
import { daftarDokumen } from '../services/api'

/** Ikon sederhana menurut jenis berkas, supaya daftarnya bisa dipindai sekilas. */
function ikon(nama, jenis) {
  if (jenis === 'gambar') return '🖼'
  if (nama.toLowerCase().endsWith('.pdf')) return '📕'
  return '📄'
}

function tanggal(iso) {
  return new Date(iso).toLocaleString('id-ID', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function PanelDokumen({ onTutup, onPilih, penanda }) {
  const [berkas, setBerkas] = useState([])
  const [galat, setGalat] = useState(null)
  const [memuat, setMemuat] = useState(true)

  // Panel ini hanya dirender saat terbuka, jadi efek ini berjalan tiap kali
  // dibuka. `penanda` memuat ulang daftarnya ketika ada unggahan baru selagi
  // panel terbuka: daftar yang basi di sini menyesatkan, karena pengguna
  // memakainya justru untuk memastikan unggahannya berhasil.
  useEffect(() => {
    let batal = false
    daftarDokumen()
      .then((d) => {
        if (batal) return
        setBerkas(d)
        setGalat(null)
      })
      .catch((e) => !batal && setGalat(e.message))
      .finally(() => !batal && setMemuat(false))
    return () => {
      batal = true
    }
  }, [penanda])

  useEffect(() => {
    const tutupDenganEsc = (e) => e.key === 'Escape' && onTutup()
    window.addEventListener('keydown', tutupDenganEsc)
    return () => window.removeEventListener('keydown', tutupDenganEsc)
  }, [onTutup])

  const jumlahGambar = berkas.filter((b) => b.jenis === 'gambar').length
  const jumlahDokumen = berkas.length - jumlahGambar

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/30 p-4 pt-16"
      onClick={onTutup}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Berkas yang sudah diunggah"
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[75vh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-xl ring-1 ring-slate-200"
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Berkas terunggah</h2>
            {!memuat && !galat && (
              <p className="mt-0.5 text-[11px] text-slate-400">
                {jumlahDokumen} dokumen · {jumlahGambar} gambar
              </p>
            )}
          </div>
          <button
            onClick={onTutup}
            aria-label="Tutup"
            className="rounded px-2 text-lg leading-none text-slate-400 transition hover:text-slate-700"
          >
            ×
          </button>
        </div>

        <div className="scroll-halus flex-1 overflow-y-auto p-2">
          {memuat && <p className="px-2 py-3 text-xs text-slate-400">Memuat…</p>}
          {galat && <p className="px-2 py-3 text-xs text-rose-600">{galat}</p>}
          {!memuat && !galat && berkas.length === 0 && (
            <p className="px-2 py-6 text-center text-xs text-slate-400">
              Belum ada berkas yang diunggah.
            </p>
          )}

          <ul className="space-y-0.5">
            {berkas.map((b) => (
              <li key={`${b.jenis}-${b.filename}`}>
                <button
                  onClick={() => onPilih(b)}
                  title={`Tanyakan tentang ${b.filename}`}
                  className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left transition hover:bg-indigo-50"
                >
                  <span aria-hidden className="text-base leading-none">
                    {ikon(b.filename, b.jenis)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-slate-700">
                      {b.filename}
                    </span>
                    <span className="mt-0.5 block text-[11px] text-slate-400">
                      {/* Gambar memang nol potongan: teksnya baru dibaca saat
                          ditanyakan, bukan saat diunggah. Dijelaskan di sini
                          supaya angka 0 tidak terbaca sebagai kegagalan. */}
                      {b.jenis === 'gambar'
                        ? 'gambar · dibaca saat ditanyakan'
                        : `${b.chunks} potongan terindeks`}
                      {' · '}
                      {tanggal(b.created_at)}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
