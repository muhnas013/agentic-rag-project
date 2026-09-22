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
  besar: 'h-11 w-11 rounded-2xl text-xl',
}

export function Lambang({ ukuran = 'kecil' }) {
  return (
    <span
      aria-hidden
      className={`flex shrink-0 items-center justify-center border border-garis bg-naik font-semibold text-terang ${UKURAN[ukuran]}`}
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
