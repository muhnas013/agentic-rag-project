/**
 * Daftar berkas yang sudah diunggah (PRD §15).
 *
 * Dibuat sebagai panel yang dibuka dari header, bukan bagian tetap sidebar:
 * sidebar sudah dipakai riwayat percakapan dan disembunyikan pada layar
 * sempit, sedangkan daftar dokumen justru perlu tetap terjangkau di sana.
 */
import { useEffect, useState } from 'react'
import { daftarDokumen } from '../services/api'
import {
  IkonBerkas,
  IkonCari,
  IkonGambar,
  IkonKlip,
  IkonPanahKanan,
  IkonSilang,
} from './Ikon'

/** Ikon menurut jenis berkas, supaya daftarnya bisa dipindai sekilas. */
function ikon(jenis) {
  return jenis === 'gambar' ? IkonGambar : IkonBerkas
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
  const [cari, setCari] = useState('')

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

  const kata = cari.trim().toLowerCase()
  const tampil = kata
    ? berkas.filter((b) => b.filename.toLowerCase().includes(kata))
    : berkas

  const jumlahGambar = berkas.filter((b) => b.jenis === 'gambar').length
  const jumlahDokumen = berkas.length - jumlahGambar

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 p-4 pt-16 backdrop-blur-sm"
      onClick={onTutup}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Berkas yang sudah diunggah"
        onClick={(e) => e.stopPropagation()}
        className="animate-naik flex max-h-[75vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-panel shadow-2xl shadow-black/50 ring-1 ring-garis"
      >
        <div className="flex items-start justify-between gap-3 border-b border-garis px-4 py-3.5">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold tracking-tight text-terang">
              Berkas terunggah
            </h2>
            {!memuat && !galat && (
              <p className="mt-0.5 text-[11px] text-redup">
                {jumlahDokumen} dokumen · {jumlahGambar} gambar
              </p>
            )}
          </div>
          <button
            onClick={onTutup}
            aria-label="Tutup"
            className="-mr-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-redup transition hover:bg-naik hover:text-terang"
          >
            <IkonSilang ukuran={15} />
          </button>
        </div>

        {/* Pencarian muncul hanya ketika daftarnya cukup panjang untuk
            menyulitkan — pada lima berkas, kolom ini justru mengganggu. */}
        {berkas.length > 8 && (
          <div className="border-b border-garis px-4 py-2.5">
            <div className="flex h-9 items-center gap-2 rounded-lg border border-garis bg-naik px-3 transition focus-within:border-garis2">
              <IkonCari ukuran={15} className="text-redup" />
              <input
                value={cari}
                onChange={(e) => setCari(e.target.value)}
                placeholder="Cari nama berkas…"
                className="min-w-0 flex-1 bg-transparent text-sm text-terang outline-none placeholder:text-redup"
              />
            </div>
          </div>
        )}

        <div className="scroll-halus flex-1 overflow-y-auto p-2">
          {memuat && (
            <div className="space-y-2 p-2">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="flex animate-pulse items-center gap-3">
                  <div className="h-8 w-8 shrink-0 rounded-lg bg-naik" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3 w-2/5 rounded bg-naik" />
                    <div className="h-2 w-3/5 rounded bg-naik" />
                  </div>
                </div>
              ))}
            </div>
          )}
          {galat && <p className="px-2 py-3 text-xs text-rose-400">{galat}</p>}
          {!memuat && !galat && berkas.length === 0 && (
            <p className="flex flex-col items-center gap-1.5 px-2 py-8 text-center text-xs leading-relaxed text-redup">
              <IkonKlip ukuran={18} />
              Belum ada berkas yang diunggah.
              <br />
              Pakai tombol lampiran di kolom pertanyaan untuk menambahkan.
            </p>
          )}
          {!memuat && !galat && berkas.length > 0 && tampil.length === 0 && (
            <p className="px-2 py-8 text-center text-xs text-redup">
              Tidak ada berkas bernama “{cari}”.
            </p>
          )}

          <ul className="space-y-0.5">
            {tampil.map((b) => {
              const Ikon = ikon(b.jenis)
              return (
              <li key={`${b.jenis}-${b.filename}`}>
                <button
                  onClick={() => onPilih(b)}
                  title={`Tanyakan tentang ${b.filename}`}
                  className="group flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition hover:bg-naik"
                >
                  <span
                    aria-hidden
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-naik text-redup transition group-hover:bg-naik2 group-hover:text-sedang"
                  >
                    <Ikon ukuran={15} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-sedang transition group-hover:text-terang">
                      {b.filename}
                    </span>
                    <span className="mt-0.5 block truncate text-[11px] text-redup">
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
                  <IkonPanahKanan
                    ukuran={14}
                    className="mr-1 text-redup opacity-0 transition group-hover:text-terang group-hover:opacity-100"
                  />
                </button>
              </li>
              )
            })}
          </ul>
        </div>

        <p className="border-t border-garis px-4 py-2.5 text-center text-[11px] text-redup">
          Pilih satu berkas untuk menyiapkan pertanyaannya.
        </p>
      </div>
    </div>
  )
}
