/**
 * Antarmuka percakapan (PRD §15).
 *
 * Memuat riwayat sesi dari backend saat dibuka, mengirim pertanyaan ke
 * Agent, dan menampilkan tool yang dipakai beserta potongan dokumen
 * sumbernya.
 *
 * Lebar bacaan dibatasi di dalam sini, bukan oleh induknya: daerah gulir
 * dan bilah masukan sama-sama membentang penuh, dan hanya isinya yang
 * dipusatkan. Membatasi induknya membuat bilah masukan tampak sebagai
 * pulau terpisah dengan celah di kiri dan kanannya.
 */
import { useEffect, useImperativeHandle, useRef, useState } from 'react'
import { ambilRiwayat, kirimPesan } from '../services/api'
import { Lambang } from './Merek'
import MessageBubble from './MessageBubble'
import UploadButton from './UploadButton'

/**
 * Contoh pertanyaan, satu untuk tiap tool.
 *
 * Kata "menurut dokumen" pada contoh pertama disengaja: tanpa petunjuk itu
 * model 3B kerap memilih SQL_Query dan menjawab ngawur. Contoh yang buruk
 * membuat kesan pertama buruk, jadi ketiganya dipilih dari pertanyaan yang
 * sudah terbukti dirutekan dengan benar.
 */
const CONTOH = [
  {
    ikon: '📄',
    tool: 'RAG_Search',
    teks: 'Menurut dokumen kebijakan, berapa lama masa retensi dokumen kepegawaian?',
  },
  {
    ikon: '🗄',
    tool: 'SQL_Query',
    teks: 'Ada berapa pegawai di bagian Keuangan?',
  },
  {
    ikon: '🖼',
    tool: 'Image_OCR',
    teks: 'Berapa total transaksi pada struk-uji.png?',
  },
]

export default function ChatBox({ ref, peran, sessionId, onPesanBaru, onUnggah }) {
  const [pesan, setPesan] = useState([])
  const [masukan, setMasukan] = useState('')
  const [menunggu, setMenunggu] = useState(false)
  const [memuatRiwayat, setMemuatRiwayat] = useState(true)
  const ujungRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    setPesan([])
    setMemuatRiwayat(true)
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

  // Dipakai panel dokumen untuk menyiapkan awal pertanyaan, dengan alasan
  // yang sama seperti setelah unggahan: menyebut nama berkas secara eksplisit
  // selalu tepat, sedangkan "dokumen tadi" tidak (B-29).
  useImperativeHandle(ref, () => ({
    siapkanPertanyaan(teks) {
      setMasukan(teks)
      inputRef.current?.focus()
    },
  }), [])

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
      // Judul dan urutan di sidebar ikut berubah setelah pesan tersimpan.
      onPesanBaru?.()
    }
  }

  function tanganiUnggahan(hasil) {
    const pesanHasil =
      hasil.status === 'processed'
        ? `Dokumen "${hasil.filename}" tersimpan dan diindeks menjadi ${hasil.chunks} potongan.`
        : `Gambar "${hasil.filename}" tersimpan.`
    tambah({ role: 'system', content: pesanHasil })

    // Nama berkas langsung diisikan ke kolom pertanyaan.
    //
    // Tanpa ini, pertanyaan sewajarnya seperti "jelaskan isi pdf tadi" tidak
    // bisa diandalkan: model 3B tidak cukup patuh menyimpulkan bahwa yang
    // dimaksud adalah unggahan terakhir, sehingga jawabannya bisa diambil
    // dari dokumen lain. Menyebut namanya secara eksplisit selalu tepat —
    // jadi namanya disiapkan di sini, bukan dibebankan pada pengguna untuk
    // mengetiknya kembali.
    setMasukan(
      hasil.status === 'processed'
        ? `Menurut dokumen ${hasil.filename}, `
        : `Apa isi gambar ${hasil.filename}? `,
    )
    inputRef.current?.focus()
    onUnggah?.()
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="scroll-halus flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl space-y-5 px-4 py-6 sm:px-6">
          {memuatRiwayat && (
            <div className="flex justify-center pt-10">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-merek-500" />
            </div>
          )}

          {!memuatRiwayat && pesan.length === 0 && (
            <div className="flex min-h-[calc(100vh-16rem)] flex-col items-center justify-center text-center">
              <Lambang ukuran="besar" />
              <h2 className="mt-5 text-xl font-semibold tracking-tight text-slate-800">
                Tanyakan apa saja tentang dokumen dan data Anda
              </h2>
              <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-500">
                Agent memilih sendiri caranya: mencari di dokumen, membaca
                gambar, atau mengambil data dari database.
              </p>

              <div className="mt-7 grid w-full max-w-xl gap-2.5 sm:grid-cols-3">
                {CONTOH.map((contoh) => (
                  <button
                    key={contoh.teks}
                    onClick={() => kirim(contoh.teks)}
                    className="group flex h-full flex-col gap-2 rounded-xl border border-slate-200 bg-white p-3.5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-merek-200 hover:shadow-md"
                  >
                    <span className="flex items-center gap-1.5">
                      <span aria-hidden className="text-base leading-none">
                        {contoh.ikon}
                      </span>
                      <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400 transition group-hover:text-merek-600">
                        {contoh.tool}
                      </span>
                    </span>
                    <span className="text-[13px] leading-snug text-slate-600 transition group-hover:text-slate-900">
                      {contoh.teks}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {pesan.map((m) =>
            m.role === 'system' && !m.error ? (
              <p
                key={m.id}
                className="animate-muncul mx-auto flex w-fit max-w-xl items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3.5 py-1.5 text-xs text-emerald-800"
              >
                <span aria-hidden>✓</span>
                {m.content}
              </p>
            ) : (
              <MessageBubble key={m.id} message={m} />
            ),
          )}

          {menunggu && (
            <div className="animate-muncul flex items-start gap-2.5">
              <Lambang />
              <div className="flex items-center gap-2 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                <span className="flex gap-1">
                  {[0, 150, 300].map((jeda) => (
                    <span
                      key={jeda}
                      style={{ animationDelay: `${jeda}ms` }}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-merek-500/70"
                    />
                  ))}
                </span>
                Agent sedang bekerja…
              </div>
            </div>
          )}

          <div ref={ujungRef} />
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          kirim(masukan)
        }}
        className="shrink-0 border-t border-slate-200 bg-white/85 py-3 backdrop-blur"
      >
        {/* Padding mendatarnya sengaja sama persis dengan daerah pesan di
            atas, sehingga tepi kotak masukan segaris dengan tepi gelembung
            percakapan. Bila berbeda sedikit saja, keduanya terbaca sebagai
            dua kolom yang tidak berhubungan. */}
        <div className="mx-auto w-full max-w-3xl px-4 sm:px-6">
          {/* Cincin fokus dipasang pada pembungkusnya, bukan pada kolom teks
              sendiri, supaya tombol lampiran dan kirim terbaca sebagai satu
              kendali bersama kolomnya. */}
          <div className="flex items-center gap-2 rounded-2xl border border-slate-300 bg-white p-1.5 shadow-sm transition focus-within:border-merek-400 focus-within:ring-4 focus-within:ring-merek-100">
            {/* READ_ONLY tidak berwenang mengunggah; tombolnya disembunyikan
                supaya tidak menawarkan aksi yang pasti ditolak 403. */}
            {peran !== 'READ_ONLY' && (
              <UploadButton
                nonaktif={menunggu}
                onSelesai={tanganiUnggahan}
                onGagal={(msg) => tambah({ role: 'system', content: msg, error: true })}
              />
            )}
            <input
              ref={inputRef}
              value={masukan}
              onChange={(e) => setMasukan(e.target.value)}
              placeholder="Tulis pertanyaan…"
              disabled={menunggu}
              className="h-9 min-w-0 flex-1 bg-transparent px-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={menunggu || !masukan.trim()}
              title="Kirim"
              className="flex h-9 shrink-0 items-center gap-1.5 rounded-xl bg-merek-600 px-3.5 text-sm font-medium text-white shadow-sm transition hover:bg-merek-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none"
            >
              <span className="hidden sm:inline">Kirim</span>
              <span aria-hidden>↑</span>
            </button>
          </div>
          <p className="mt-2 text-center text-[11px] text-slate-400">
            Jawaban disusun model lokal dari dokumen Anda — periksa kembali
            angka dan tanggal sebelum dipakai.
          </p>
        </div>
      </form>
    </div>
  )
}
