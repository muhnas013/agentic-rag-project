/**
 * Satu gelembung percakapan (PRD §15).
 *
 * Jawaban asisten dirender sebagai Markdown karena model kerap memakai
 * penebalan dan daftar bernomor; ditampilkan mentah, format itu justru
 * mengganggu keterbacaan.
 */
import Markdown from 'react-markdown'

function LencanaTool({ tool }) {
  if (!tool || tool === 'none') return null
  return (
    <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-indigo-200">
      {tool}
    </span>
  )
}

function DaftarSumber({ sources }) {
  if (!sources?.length) return null
  return (
    <details className="mt-3 border-t border-slate-200 pt-2">
      <summary className="cursor-pointer text-xs font-medium text-slate-500 hover:text-slate-700">
        {sources.length} potongan dokumen dipakai
      </summary>
      <ul className="mt-2 space-y-2">
        {sources.map((s, i) => (
          <li key={i} className="rounded-md bg-slate-50 p-2 text-xs text-slate-600">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-slate-700">{s.filename}</span>
              {/* Skor kemiripan membuat jawaban bisa ditelusuri: potongan
                  berskor rendah adalah petunjuk pertama bahwa pencarian,
                  bukan model, yang meleset. */}
              <span className="shrink-0 tabular-nums text-slate-400">
                skor {s.score?.toFixed?.(3) ?? s.score}
              </span>
            </div>
            <p className="mt-1 line-clamp-3 text-slate-500">{s.excerpt}</p>
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
      <div className="mx-auto w-full max-w-2xl rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
        {content}
      </div>
    )
  }

  return (
    <div className={dariPengguna ? 'flex justify-end' : 'flex justify-start'}>
      <div
        className={[
          'max-w-2xl rounded-2xl px-4 py-3 text-sm shadow-sm',
          dariPengguna
            ? 'bg-indigo-600 text-white'
            : 'border border-slate-200 bg-white text-slate-800',
        ].join(' ')}
      >
        {!dariPengguna && tool && (
          <div className="mb-2">
            <LencanaTool tool={tool} />
          </div>
        )}

        {dariPengguna ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose-sm space-y-2 [&_li]:ml-4 [&_li]:list-disc [&_ol_li]:list-decimal [&_strong]:font-semibold">
            <Markdown>{content}</Markdown>
          </div>
        )}

        {!dariPengguna && <DaftarSumber sources={sources} />}
      </div>
    </div>
  )
}
