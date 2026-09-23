/**
 * Tombol memilih berkas untuk dilampirkan (PRD §15 dan §20).
 *
 * Hanya membuka pemilih berkas dan menyerahkan `File` yang dipilih kepada
 * pemanggilnya. Pengunggahan dan tampilan kemajuannya dikerjakan
 * `ChatBox`, karena berkas yang sedang diunggah ditampilkan sebagai kartu
 * lampiran di atas kolom pertanyaan — bukan di dalam tombol ini.
 */
import { useRef } from 'react'
import { IkonTambah } from './Ikon'

const EKSTENSI = '.pdf,.txt,.md,.png,.jpg,.jpeg,.webp'

export default function UploadButton({ onPilih, nonaktif }) {
  const inputRef = useRef(null)

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={EKSTENSI}
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onPilih(file)
          // Direset supaya berkas yang sama bisa dipilih lagi setelah
          // dilepas atau setelah gagal.
          e.target.value = ''
        }}
        className="hidden"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={nonaktif}
        title="Lampirkan dokumen atau gambar"
        aria-label="Lampirkan dokumen atau gambar"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sedang transition hover:bg-naik2 hover:text-terang disabled:cursor-not-allowed disabled:opacity-50"
      >
        <IkonTambah ukuran={18} />
      </button>
    </>
  )
}
