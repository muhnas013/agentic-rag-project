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
        aria-label="Unggah dokumen atau gambar"
        className="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-xl text-redup transition hover:bg-naik2 hover:text-terang disabled:cursor-not-allowed disabled:opacity-50"
      >
        {sibuk ? (
          <>
            {/* Kemajuan ditampilkan sebagai latar yang naik, bukan hanya
                angka: berkas besar butuh waktu, dan gerakan memberi tahu
                bahwa prosesnya masih hidup. */}
            <span
              aria-hidden
              className="absolute inset-x-0 bottom-0 bg-naik2 transition-[height] duration-200"
              style={{ height: `${progres}%` }}
            />
            <span className="relative text-[10px] font-semibold tabular-nums text-terang">
              {progres}%
            </span>
          </>
        ) : (
          <span aria-hidden className="text-base">📎</span>
        )}
      </button>
    </>
  )
}
