/**
 * Satu giliran percakapan (PRD §15).
 *
 * Jawaban asisten dirender sebagai Markdown karena model kerap memakai
 * penebalan dan daftar bernomor; ditampilkan mentah, format itu justru
 * mengganggu keterbacaan.
 *
 * Mengikuti gaya Grok, jawaban asisten **tidak** diberi gelembung: hanya
 * pertanyaan pengguna yang berlatar. Jawaban biasanya jauh lebih panjang
 * daripada pertanyaannya, dan membungkusnya dalam kotak membuat blok teks
 * panjang terasa sesak. Pertanyaan yang pendek justru terbantu oleh latar
 * itu untuk membedakan giliran siapa.
 */
import Markdown from 'react-markdown'
import { pisahLampiran } from '../services/lampiran'
import { IkonBerkas, IkonGambar, IkonPanahKanan, IkonPeringatan } from './Ikon'

function LencanaTool({ tool }) {
  if (!tool || tool === 'none') return null
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-garis bg-naik px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-sedang">
      <span aria-hidden className="h-1 w-1 rounded-full bg-sedang" />
      {tool}
    </span>
  )
}

/**
 * Skor kemiripan ditampilkan sebagai bilah, bukan angka saja.
 *
 * Angka 0,042 tidak berarti apa-apa bagi pembaca sampai ia tahu rentangnya;
 * panjang bilah relatif terhadap potongan terbaik langsung memperlihatkan
 * mana yang kuat dan mana yang ikut terbawa.
 */
function BilahSkor({ skor, tertinggi }) {
  const rasio = tertinggi > 0 ? Math.max(skor / tertinggi, 0.04) : 0
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-1 w-10 overflow-hidden rounded-full bg-garis2">
        <span
          className="block h-full rounded-full bg-sedang"
          style={{ width: `${rasio * 100}%` }}
        />
      </span>
      <span className="tabular-nums text-redup">{skor?.toFixed?.(3) ?? skor}</span>
    </span>
  )
}

function DaftarSumber({ sources }) {
  if (!sources?.length) return null
  const tertinggi = Math.max(...sources.map((s) => s.score ?? 0))

  return (
    <details className="group/sumber mt-4">
      <summary className="flex w-fit cursor-pointer list-none items-center gap-1.5 rounded-full border border-garis px-3 py-1 text-xs text-redup transition hover:border-garis2 hover:text-sedang">
        <IkonPanahKanan
          ukuran={13}
          className="transition group-open/sumber:rotate-90"
        />
        {sources.length} potongan dokumen dipakai
      </summary>
      <ul className="mt-2.5 space-y-1.5">
        {sources.map((s, i) => (
          <li
            key={i}
            className="rounded-xl border border-garis bg-panel p-3 text-xs text-sedang"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-medium text-terang">{s.filename}</span>
              {/* Skor kemiripan membuat jawaban bisa ditelusuri: potongan
                  berskor rendah adalah petunjuk pertama bahwa pencarian,
                  bukan model, yang meleset. */}
              <BilahSkor skor={s.score} tertinggi={tertinggi} />
            </div>
            <p className="mt-1.5 line-clamp-3 leading-relaxed text-redup">
              {s.excerpt}
            </p>
          </li>
        ))}
      </ul>
    </details>
  )
}

/**
 * Berkas yang dilampirkan pada pertanyaan, tampil sebagai kartu di atas
 * gelembungnya — bukan disisipkan ke dalam kalimat pengguna.
 *
 * Nama berkas memang ikut terkirim ke model (lihat `services/lampiran.js`),
 * tetapi menampilkannya di dalam kalimat membuat pengguna membaca sesuatu
 * yang tidak ia tulis.
 */
function KartuBerkasPesan({ lampiran }) {
  const Ikon = lampiran.jenis === 'gambar' ? IkonGambar : IkonBerkas
  const ekst = (lampiran.nama.split('.').pop() || '').toUpperCase()
  return (
    <div className="mb-1.5 flex justify-end">
      <div className="flex w-full max-w-sm items-center gap-2.5 rounded-2xl border border-garis bg-naik px-3 py-2.5">
        <span
          aria-hidden
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-naik2 text-sedang"
        >
          <Ikon ukuran={16} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-medium text-terang">
            {lampiran.nama}
          </span>
          <span className="mt-0.5 block text-[11px] text-redup">
            {lampiran.jenis === 'gambar' ? `Gambar ${ekst}` : ekst || 'Dokumen'}
          </span>
        </span>
      </div>
    </div>
  )
}

export default function MessageBubble({ message }) {
  const { role, content, tool, sources, error } = message
  const dariPengguna = role === 'user'

  if (error) {
    return (
      <div className="animate-muncul flex items-start gap-2.5 rounded-xl border border-rose-900/60 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">
        <IkonPeringatan ukuran={16} className="mt-0.5" />
        <span>{content}</span>
      </div>
    )
  }

  if (dariPengguna) {
    // Rujukan berkas dibaca kembali dari teks yang tersimpan, sehingga
    // pesan baru dan pesan yang dimuat ulang dari riwayat tampil sama.
    const { lampiran, teks } = pisahLampiran(content)
    return (
      <div className="animate-muncul">
        {lampiran && <KartuBerkasPesan lampiran={lampiran} />}
        <div className="flex justify-end">
          <div className="max-w-[85%] rounded-3xl rounded-br-lg border border-garis bg-naik px-4 py-2.5 text-[15px] leading-relaxed text-terang">
            <p className="whitespace-pre-wrap">{teks}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-muncul">
      {tool && (
        <div className="mb-2">
          <LencanaTool tool={tool} />
        </div>
      )}

      <div className="space-y-3 text-[15px] leading-relaxed text-terang [&_a]:text-sedang [&_a]:underline [&_code]:rounded [&_code]:bg-naik [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[13px] [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:text-base [&_h2]:font-semibold [&_h3]:font-semibold [&_li]:ml-4 [&_li]:list-disc [&_ol_li]:list-decimal [&_pre]:overflow-x-auto [&_pre]:rounded-xl [&_pre]:border [&_pre]:border-garis [&_pre]:bg-panel [&_pre]:p-3 [&_strong]:font-semibold [&_table]:block [&_table]:w-full [&_table]:overflow-x-auto [&_td]:border [&_td]:border-garis [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-garis [&_th]:bg-panel [&_th]:px-2 [&_th]:py-1">
        <Markdown>{content}</Markdown>
      </div>

      <DaftarSumber sources={sources} />
    </div>
  )
}
