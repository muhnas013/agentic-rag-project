/**
 * Tombol unggah dokumen atau gambar (PRD §15 dan §20).
 *
 * Backend membedakan keduanya: dokumen langsung diolah menjadi embedding
 * (`status: processed`), sedangkan gambar hanya disimpan (`status: stored`)
 * dan baru dibaca ketika pengguna menanyakannya — OCR dijalankan Agent,
 * bukan saat unggah. Perbedaan itu disampaikan lewat pesan hasil.
 */
import { useRef, useState } from 'react'
import { unggahBerkas } from '../services/api'

const EKSTENSI = '.pdf,.txt,.md,.png,.jpg,.jpeg,.webp'

export default function UploadButton({ onSelesai, onGagal, nonaktif }) {
  const inputRef = useRef(null)
  const [progres, setProgres] = useState(null)

  async function tangani(event) {
    const file = event.target.files?.[0]
    if (!file) return

    setProgres(0)
    try {
      const hasil = await unggahBerkas(file, setProgres)
      onSelesai?.(hasil)
    } catch (error) {
      onGagal?.(error.message)
    } finally {
      setProgres(null)
      // Direset supaya berkas yang sama bisa dipilih lagi setelah gagal.
      event.target.value = ''
    }
  }

  const sibuk = progres !== null

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={EKSTENSI}
        onChange={tangani}
        className="hidden"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={nonaktif || sibuk}
        title="Unggah dokumen atau gambar"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-300 text-slate-500 transition hover:border-slate-400 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {sibuk ? (
          <span className="text-xs font-medium tabular-nums">{progres}%</span>
        ) : (
          <span aria-hidden className="text-lg">📎</span>
        )}
      </button>
    </>
  )
}
