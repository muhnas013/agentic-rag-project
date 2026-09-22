/**
 * Satu gelembung percakapan (PRD §15).
 *
 * Jawaban asisten dirender sebagai Markdown karena model kerap memakai
 * penebalan dan daftar bernomor; ditampilkan mentah, format itu justru
 * mengganggu keterbacaan.
 */
import Markdown from 'react-markdown'
import { Lambang } from './Merek'

/** Warna lencana mengikuti tool, supaya jalur jawaban terbaca sekilas. */
const WARNA_TOOL = {
  RAG_Search: 'bg-merek-50 text-merek-700 ring-merek-200',
  SQL_Query: 'bg-amber-50 text-amber-800 ring-amber-200',
  Image_OCR: 'bg-teal-50 text-teal-800 ring-teal-200',
}

function LencanaTool({ tool }) {
  if (!tool || tool === 'none') return null
  const warna = WARNA_TOOL[tool] ?? 'bg-slate-100 text-slate-600 ring-slate-200'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ring-1 ${warna}`}
    >
      {tool}
    </span>
  )
}

/**
 * Skor kemiripan ditampilkan sebagai bilah, bukan angka saja.
 *
 * Angka 0,043 tidak berarti apa-apa bagi pembaca sampai ia tahu rentangnya;
 * panjang bilah relatif terhadap potongan terbaik langsung memperlihatkan
 * mana yang kuat dan mana yang ikut terbawa.
 */
function BilahSkor({ skor, tertinggi }) {
  const rasio = tertinggi > 0 ? Math.max(skor / tertinggi, 0.04) : 0
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-1 w-10 overflow-hidden rounded-full bg-slate-200">
        <span
          className="block h-full rounded-full bg-merek-500/70"
          style={{ width: `${rasio * 100}%` }}
        />
      </span>
      <span className="tabular-nums text-slate-400">
        {skor?.toFixed?.(3) ?? skor}
      </span>
    </span>
  )
}

function DaftarSumber({ sources }) {
  if (!sources?.length) return null
  const tertinggi = Math.max(...sources.map((s) => s.score ?? 0))

  return (
    <details className="group/sumber mt-3 border-t border-slate-100 pt-2.5">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 text-xs font-medium text-slate-500 transition hover:text-slate-800">
        <span
          aria-hidden
          className="transition group-open/sumber:rotate-90"
        >
          ›
        </span>
        {sources.length} potongan dokumen dipakai
      </summary>
      <ul className="mt-2 space-y-1.5">
        {sources.map((s, i) => (
          <li
            key={i}
            className="rounded-lg border border-slate-100 bg-slate-50/70 p-2.5 text-xs text-slate-600"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-medium text-slate-700">
                {s.filename}
              </span>
              {/* Skor kemiripan membuat jawaban bisa ditelusuri: potongan
                  berskor rendah adalah petunjuk pertama bahwa pencarian,
                  bukan model, yang meleset. */}
              <BilahSkor skor={s.score} tertinggi={tertinggi} />
            </div>
            <p className="mt-1.5 line-clamp-3 leading-relaxed text-slate-500">
              {s.excerpt}
            </p>
          </li>
        ))}
      </ul>
    </details>
  )
}

export default function MessageBubble({ message }) {
  const { role, content, tool, sources, error } = message
  const dariPengguna = role === 'user'

  if (error) {
    return (
      <div className="animate-muncul mx-auto flex w-full max-w-2xl items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
        <span aria-hidden className="mt-px shrink-0">
          ⚠
        </span>
        <span>{content}</span>
      </div>
    )
  }

  if (dariPengguna) {
    return (
      <div className="animate-muncul flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-merek-600 px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-sm">
          <p className="whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-muncul flex items-start gap-2.5">
      <Lambang />
      <div className="min-w-0 max-w-[85%] rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 text-[15px] leading-relaxed text-slate-800 shadow-sm">
        {tool && (
          <div className="mb-2">
            <LencanaTool tool={tool} />
          </div>
        )}

        <div className="space-y-2.5 [&_a]:text-merek-700 [&_a]:underline [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[13px] [&_li]:ml-4 [&_li]:list-disc [&_ol_li]:list-decimal [&_strong]:font-semibold [&_table]:block [&_table]:w-full [&_table]:overflow-x-auto [&_td]:border [&_td]:border-slate-200 [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-slate-200 [&_th]:bg-slate-50 [&_th]:px-2 [&_th]:py-1">
          <Markdown>{content}</Markdown>
        </div>

        <DaftarSumber sources={sources} />
      </div>
    </div>
  )
}
