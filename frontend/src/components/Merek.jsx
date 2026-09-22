/**
 * Tanda merek: lambang dan nama aplikasi.
 *
 * Dipakai di header, layar masuk, dan layar percakapan kosong. Dijadikan
 * satu komponen supaya ketiganya tidak pelan-pelan berbeda satu sama lain
 * setiap kali salah satunya disentuh.
 */

const UKURAN = {
  kecil: 'h-7 w-7 rounded-lg text-[13px]',
  sedang: 'h-9 w-9 rounded-xl text-base',
  besar: 'h-12 w-12 rounded-2xl text-xl',
}

export function Lambang({ ukuran = 'kecil' }) {
  return (
    <span
      aria-hidden
      className={`flex shrink-0 items-center justify-center bg-gradient-to-br from-merek-500 to-merek-700 font-semibold text-white shadow-sm ring-1 ring-merek-700/20 ${UKURAN[ukuran]}`}
    >
      ◈
    </span>
  )
}

export default function Merek({ ukuran = 'kecil', keterangan }) {
  return (
    <div className="flex items-center gap-2.5">
      <Lambang ukuran={ukuran} />
      <div className="min-w-0">
        <p
          className={`truncate font-semibold tracking-tight text-slate-800 ${
            ukuran === 'besar' ? 'text-lg' : 'text-sm'
          }`}
        >
          Agentic RAG
        </p>
        {keterangan && (
          <p className="truncate text-xs text-slate-500">{keterangan}</p>
        )}
      </div>
    </div>
  )
}
