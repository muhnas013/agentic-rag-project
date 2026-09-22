/**
 * Daftar percakapan dan tombol memulai percakapan baru (PRD §15 - Chat history).
 */
import { useEffect, useState } from 'react'
import { daftarSesi, hapusSesi } from '../services/api'

/**
 * Kelompokkan percakapan menurut kedekatan waktunya.
 *
 * "Hari ini" dan "Kemarin" jauh lebih mudah ditangkap sekilas daripada
 * tanggal, dan itulah dua kelompok yang paling sering dicari.
 */
function kelompokkan(sesi) {
  const hariIni = new Date()
  hariIni.setHours(0, 0, 0, 0)
  const kemarin = new Date(hariIni)
  kemarin.setDate(kemarin.getDate() - 1)
  const pekanIni = new Date(hariIni)
  pekanIni.setDate(pekanIni.getDate() - 7)

  const kelompok = new Map()
  for (const s of sesi) {
    const waktu = new Date(s.terakhir)
    let label
    if (waktu >= hariIni) label = 'Hari ini'
    else if (waktu >= kemarin) label = 'Kemarin'
    else if (waktu >= pekanIni) label = '7 hari terakhir'
    else label = 'Lebih lama'

    if (!kelompok.has(label)) kelompok.set(label, [])
    kelompok.get(label).push(s)
  }
  return [...kelompok.entries()]
}

function jam(iso) {
  return new Date(iso).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
}

export default function Sidebar({ sessionId, onPilih, onBaru, penanda, bolehHapus }) {
  const [sesi, setSesi] = useState([])
  const [galat, setGalat] = useState(null)
  const [memuat, setMemuat] = useState(true)

  // `penanda` berubah setiap kali ada pesan baru, sehingga daftar ikut
  // menyegarkan diri tanpa perlu dimuat ulang manual.
  useEffect(() => {
    daftarSesi()
      .then((d) => { setSesi(d); setGalat(null) })
      .catch((e) => setGalat(e.message))
      .finally(() => setMemuat(false))
  }, [penanda])

  async function hapus(e, id) {
    e.stopPropagation()
    if (!confirm('Hapus percakapan ini?')) return
    try {
      await hapusSesi(id)
      setSesi((s) => s.filter((x) => x.session_id !== id))
      if (id === sessionId) onBaru()
    } catch (error) {
      setGalat(error.message)
    }
  }

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="p-3">
        <button
          onClick={onBaru}
          className="flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-merek-600 text-sm font-medium text-white shadow-sm transition hover:bg-merek-700"
        >
          <span aria-hidden className="text-base leading-none">+</span>
          Percakapan baru
        </button>
      </div>

      <div className="scroll-halus flex-1 overflow-y-auto px-2 pb-3">
        {memuat && (
          <div className="space-y-2 px-2 pt-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse space-y-1.5">
                <div className="h-3 w-4/5 rounded bg-slate-100" />
                <div className="h-2 w-2/5 rounded bg-slate-100" />
              </div>
            ))}
          </div>
        )}
        {galat && <p className="px-2 text-xs text-rose-600">{galat}</p>}
        {!memuat && !galat && sesi.length === 0 && (
          <p className="px-2 pt-4 text-center text-xs leading-relaxed text-slate-400">
            Belum ada percakapan.
            <br />
            Pertanyaan pertama Anda akan muncul di sini.
          </p>
        )}

        {kelompokkan(sesi).map(([label, daftar]) => (
          <div key={label} className="mb-3">
            <p className="px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              {label}
            </p>
            <ul className="space-y-0.5">
              {daftar.map((s) => {
                const aktif = s.session_id === sessionId
                return (
                  <li key={s.session_id}>
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => onPilih(s.session_id)}
                      onKeyDown={(e) => e.key === 'Enter' && onPilih(s.session_id)}
                      className={[
                        // Penanda aktif berupa garis di tepi kiri, bukan hanya
                        // warna latar: pada layar dengan kontras rendah, beda
                        // warna sehalus itu mudah luput.
                        'group relative flex cursor-pointer items-start gap-1.5 rounded-lg py-2 pl-3 pr-2 text-left text-sm transition',
                        'before:absolute before:left-0 before:top-1/2 before:h-5 before:w-0.5 before:-translate-y-1/2 before:rounded-r-full before:transition',
                        aktif
                          ? 'bg-merek-50 text-merek-900 before:bg-merek-600'
                          : 'text-slate-600 before:bg-transparent hover:bg-slate-50',
                      ].join(' ')}
                    >
                      <div className="min-w-0 flex-1">
                        <p className={`truncate ${aktif ? 'font-medium' : ''}`}>
                          {s.judul}
                        </p>
                        <p className="mt-0.5 text-[11px] text-slate-400">
                          {jam(s.terakhir)} · {s.jumlah_pesan} pesan
                        </p>
                      </div>
                      {bolehHapus && (
                        <button
                          onClick={(e) => hapus(e, s.session_id)}
                          title="Hapus percakapan"
                          aria-label={`Hapus percakapan ${s.judul}`}
                          className="shrink-0 rounded px-1 text-slate-300 opacity-0 transition hover:text-rose-600 focus:opacity-100 group-hover:opacity-100"
                        >
                          ×
                        </button>
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </aside>
  )
}
