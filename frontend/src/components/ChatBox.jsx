/**
 * Antarmuka percakapan (PRD §15).
 *
 * Memuat riwayat sesi dari backend saat dibuka, mengirim pertanyaan ke
 * Agent, dan menampilkan tool yang dipakai beserta potongan dokumen
 * sumbernya.
 */
import { useEffect, useRef, useState } from 'react'
import { ambilRiwayat, kirimPesan } from '../services/api'
import MessageBubble from './MessageBubble'
import UploadButton from './UploadButton'

const KUNCI_SESI = 'agentic-rag-session'

/** Sesi disimpan di browser agar riwayat bertahan saat halaman dimuat ulang. */
function sesiTersimpan() {
  let id = localStorage.getItem(KUNCI_SESI)
  if (!id) {
    id = `sesi-${crypto.randomUUID().slice(0, 8)}`
    localStorage.setItem(KUNCI_SESI, id)
  }
  return id
}

/**
 * Contoh pertanyaan, satu untuk tiap tool.
 *
 * Kata "menurut dokumen" pada contoh pertama disengaja: tanpa petunjuk itu
 * model 3B kerap memilih SQL_Query dan menjawab ngawur. Contoh yang buruk
 * membuat kesan pertama buruk, jadi ketiganya dipilih dari pertanyaan yang
 * sudah terbukti dirutekan dengan benar.
 */
const CONTOH = [
  'Menurut dokumen kebijakan, berapa lama masa retensi dokumen kepegawaian?',
  'Ada berapa pegawai di bagian Keuangan?',
  'Berapa total transaksi pada struk-uji.png?',
]

export default function ChatBox() {
  const [sessionId] = useState(sesiTersimpan)
  const [pesan, setPesan] = useState([])
  const [masukan, setMasukan] = useState('')
  const [menunggu, setMenunggu] = useState(false)
  const [memuatRiwayat, setMemuatRiwayat] = useState(true)
  const ujungRef = useRef(null)

  useEffect(() => {
    ambilRiwayat(sessionId)
      .then((data) =>
        setPesan(
          // Riwayat tidak menyimpan sumber maupun tool; hanya isi pesannya.
          data.messages.map((m) => ({
            id: `riwayat-${m.id}`,
            role: m.role,
            content: m.message,
          })),
        ),
      )
      .catch((error) => tambah({ role: 'system', content: error.message, error: true }))
      .finally(() => setMemuatRiwayat(false))
  }, [sessionId])

  useEffect(() => {
    ujungRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [pesan, menunggu])

  function tambah(m) {
    setPesan((sebelumnya) => [...sebelumnya, { id: crypto.randomUUID(), ...m }])
  }

  async function kirim(teks) {
    const isi = teks.trim()
    if (!isi || menunggu) return

    tambah({ role: 'user', content: isi })
    setMasukan('')
    setMenunggu(true)

    try {
      const hasil = await kirimPesan({ sessionId, pesan: isi })
      tambah({
        role: 'assistant',
        content: hasil.answer,
        tool: hasil.tool_used,
        sources: hasil.sources,
      })
    } catch (error) {
      tambah({ role: 'system', content: error.message, error: true })
    } finally {
      setMenunggu(false)
    }
  }

  function tanganiUnggahan(hasil) {
    const pesanHasil =
      hasil.status === 'processed'
        ? `Dokumen "${hasil.filename}" tersimpan dan diindeks menjadi ${hasil.chunks} potongan. Silakan tanyakan isinya.`
        : `Gambar "${hasil.filename}" tersimpan. Tanyakan isinya, misalnya "Berapa total pada ${hasil.filename}?"`
    tambah({ role: 'system', content: pesanHasil })
  }

  return (
    <div className="flex h-full flex-col">
      <div className="scroll-halus flex-1 space-y-4 overflow-y-auto px-4 py-6 sm:px-6">
        {memuatRiwayat && (
          <p className="text-center text-sm text-slate-400">Memuat riwayat…</p>
        )}

        {!memuatRiwayat && pesan.length === 0 && (
          <div className="mx-auto max-w-lg pt-10 text-center">
            <h2 className="text-lg font-semibold text-slate-700">
              Tanyakan apa saja tentang dokumen dan data Anda
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              Agent memilih sendiri caranya: mencari di dokumen, membaca gambar,
              atau mengambil data dari database.
            </p>
            <div className="mt-6 space-y-2">
              {CONTOH.map((contoh) => (
                <button
                  key={contoh}
                  onClick={() => kirim(contoh)}
                  className="block w-full rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-left text-sm text-slate-600 transition hover:border-indigo-300 hover:text-indigo-700"
                >
                  {contoh}
                </button>
              ))}
            </div>
          </div>
        )}

        {pesan.map((m) =>
          m.role === 'system' && !m.error ? (
            <p
              key={m.id}
              className="mx-auto max-w-2xl rounded-lg bg-emerald-50 px-4 py-2 text-center text-xs text-emerald-800"
            >
              {m.content}
            </p>
          ) : (
            <MessageBubble key={m.id} message={m} />
          ),
        )}

        {menunggu && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
              <span className="flex gap-1">
                {[0, 150, 300].map((jeda) => (
                  <span
                    key={jeda}
                    style={{ animationDelay: `${jeda}ms` }}
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
                  />
                ))}
              </span>
              Agent sedang bekerja…
            </div>
          </div>
        )}

        <div ref={ujungRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          kirim(masukan)
        }}
        className="border-t border-slate-200 bg-white px-4 py-3 sm:px-6"
      >
        <div className="mx-auto flex max-w-3xl items-center gap-2">
          <UploadButton
            nonaktif={menunggu}
            onSelesai={tanganiUnggahan}
            onGagal={(msg) => tambah({ role: 'system', content: msg, error: true })}
          />
          <input
            value={masukan}
            onChange={(e) => setMasukan(e.target.value)}
            placeholder="Tulis pertanyaan…"
            disabled={menunggu}
            className="h-10 flex-1 rounded-lg border border-slate-300 px-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={menunggu || !masukan.trim()}
            className="h-10 rounded-lg bg-indigo-600 px-4 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Kirim
          </button>
        </div>
      </form>
    </div>
  )
}
