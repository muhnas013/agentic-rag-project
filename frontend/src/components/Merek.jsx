/**
 * Tanda merek: lambang dan nama aplikasi.
 *
 * Dipakai di header, layar masuk, dan layar percakapan kosong. Dijadikan
 * satu komponen supaya ketiganya tidak pelan-pelan berbeda satu sama lain
 * setiap kali salah satunya disentuh.
 */
import { IkonMerek } from './Ikon'

const UKURAN = {
  kecil: { kelas: 'h-7 w-7 rounded-lg', ikon: 15 },
  sedang: { kelas: 'h-9 w-9 rounded-xl', ikon: 18 },
  besar: { kelas: 'h-11 w-11 rounded-2xl', ikon: 22 },
}

export function Lambang({ ukuran = 'kecil' }) {
  const { kelas, ikon } = UKURAN[ukuran]
  return (
    <span
      aria-hidden
      className={`flex shrink-0 items-center justify-center border border-garis bg-naik text-terang ${kelas}`}
    >
      <IkonMerek ukuran={ikon} />
    </span>
  )
}

export default function Merek({ ukuran = 'kecil', keterangan }) {
  return (
    <div className="flex items-center gap-2.5">
      <Lambang ukuran={ukuran} />
      <div className="min-w-0">
        <p
          className={`truncate font-semibold tracking-tight text-terang ${
            ukuran === 'besar' ? 'text-lg' : 'text-sm'
          }`}
        >
          Agentic RAG
        </p>
        {keterangan && <p className="truncate text-xs text-redup">{keterangan}</p>}
      </div>
    </div>
  )
}
