/**
 * Antarmuka percakapan (PRD §15).
 *
 * Memuat riwayat sesi dari backend saat dibuka, mengirim pertanyaan ke
 * Agent, dan menampilkan tool yang dipakai beserta potongan dokumen
 * sumbernya.
 *
 * Susunannya mengikuti gaya Grok: selama percakapan masih kosong, kolom
 * pertanyaan berada di tengah layar bersama sapaan dan saran; begitu ada
 * pesan pertama, kolom yang sama turun menempel ke dasar. Karena itu
 * `KolomPertanyaan` dipisah menjadi komponen tersendiri — dipakai di dua
 * tempat, tetapi hanya ada satu salinan perilakunya.
 */
import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react'
import { ambilRiwayat, kirimPesan } from '../services/api'
import {
  IkonBasisData,
  IkonBerkas,
  IkonCentang,
  IkonGambar,
  IkonPanahAtas,
} from './Ikon'
import { Lambang } from './Merek'
import PemilihModel from './PemilihModel'
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
    Ikon: IkonBerkas,
    label: 'Cari di dokumen',
    teks: 'Menurut dokumen kebijakan, berapa lama masa retensi dokumen kepegawaian?',
  },
  {
    Ikon: IkonBasisData,
    label: 'Tanya database',
    teks: 'Ada berapa pegawai di bagian Keuangan?',
  },
  {
    Ikon: IkonGambar,
    label: 'Baca gambar',
    teks: 'Berapa total transaksi pada struk-uji.png?',
  },
]

/**
 * Tinggi terbesar kolom pertanyaan sebelum ia mulai bergulir sendiri.
 * Angkanya harus sama dengan kelas `max-h-52` pada elemennya: yang satu
 * mengatur tinggi lewat JavaScript, yang lain menjadi batas keras bila
 * perhitungan itu meleset.
 */
const TINGGI_MAKS = 208

function KolomPertanyaan({
  inputRef,
  nilai,
  onUbah,
  onKirim,
  menunggu,
  peran,
  model,
  onPilihModel,
  onUnggahSelesai,
  onUnggahGagal,
}) {
  // Tinggi kolom mengikuti isinya.
  //
  // Dikerjakan lewat efek, bukan di dalam `onChange`, supaya semua jalur
  // yang mengubah isinya ikut tertangani — termasuk yang tidak lewat
  // ketikan: mengosongkan kolom setelah kirim, dan mengisinya dari panel
  // dokumen maupun setelah unggahan.
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    // Dinolkan lebih dulu; tanpa itu `scrollHeight` tidak pernah mengecil
    // dan kolomnya hanya bisa membesar, tidak bisa menyusut kembali.
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, TINGGI_MAKS)}px`
  }, [nilai, inputRef])

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        onKirim(nilai)
      }}
    >
      {/* Kolom teks di atas, deretan tombol di bawahnya — bukan satu baris
          bersama. Pada pertanyaan panjang, susunan satu baris menyisakan
          kolom teks yang sempit terjepit di antara dua tombol. */}
      <div className="rounded-3xl border border-garis bg-naik p-2.5 shadow-lg shadow-black/20 transition focus-within:border-garis2">
        <textarea
          ref={inputRef}
          rows={1}
          value={nilai}
          onChange={(e) => onUbah(e.target.value)}
          onKeyDown={(e) => {
            // Enter mengirim, Shift+Enter menambah baris.
            //
            // `isComposing` diperiksa karena papan ketik yang memakai
            // penyusunan aksara — IME — juga memakai Enter untuk memilih
            // kandidat. Tanpa pemeriksaan ini, pertanyaan akan terkirim
            // separuh jadi tepat saat penggunanya sedang mengetik.
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              onKirim(nilai)
            }
          }}
          placeholder="Tanyakan apa saja…"
          disabled={menunggu}
          className="scroll-halus block max-h-52 w-full resize-none bg-transparent px-2 py-1.5 text-[15px] leading-6 text-terang outline-none placeholder:text-redup disabled:opacity-60"
        />

        <div className="mt-1 flex items-center justify-between gap-2">
          {/* READ_ONLY tidak berwenang mengunggah; tombolnya disembunyikan
              supaya tidak menawarkan aksi yang pasti ditolak 403. */}
          <div className="flex min-w-0 items-center gap-1">
            {peran !== 'READ_ONLY' && (
              <UploadButton
                nonaktif={menunggu}
                onSelesai={onUnggahSelesai}
                onGagal={onUnggahGagal}
              />
            )}
            <PemilihModel
              nilai={model}
              onPilih={onPilihModel}
              nonaktif={menunggu}
            />
          </div>

          <button
            type="submit"
            disabled={menunggu || !nilai.trim()}
            title="Kirim"
            aria-label="Kirim"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-terang text-base font-semibold text-dasar transition hover:opacity-90 disabled:cursor-not-allowed disabled:bg-naik2 disabled:text-redup"
          >
            <IkonPanahAtas ukuran={16} />
          </button>
        </div>
      </div>
    </form>
  )
}

/** Pilihan model bertahan antar sesi, tetapi hanya di peramban ini. */
const KUNCI_MODEL = 'agentic-rag-model'

export default function ChatBox({ ref, peran, sessionId, onPesanBaru, onUnggah }) {
  const [model, setModel] = useState(() => localStorage.getItem(KUNCI_MODEL))
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

  const pilihModel = useCallback((nama) => {
    setModel(nama)
    if (nama) localStorage.setItem(KUNCI_MODEL, nama)
    else localStorage.removeItem(KUNCI_MODEL)
  }, [])

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
      const hasil = await kirimPesan({ sessionId, pesan: isi, model })
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

  const kolom = (
    <KolomPertanyaan
      inputRef={inputRef}
      nilai={masukan}
      onUbah={setMasukan}
      onKirim={kirim}
      menunggu={menunggu}
      peran={peran}
      model={model}
      onPilihModel={pilihModel}
      onUnggahSelesai={tanganiUnggahan}
      onUnggahGagal={(msg) => tambah({ role: 'system', content: msg, error: true })}
    />
  )

  const kosong = !memuatRiwayat && pesan.length === 0

  // Percakapan kosong: sapaan, kolom pertanyaan, lalu saran — semuanya di
  // tengah layar. Tidak ada daerah gulir dan tidak ada bilah bawah, jadi
  // tidak ada ruang kosong menganga di antara keduanya.
  if (kosong) {
    return (
      <div className="flex h-full min-h-0 flex-col items-center justify-center px-4 pb-10">
        <div className="w-full max-w-2xl">
          <div className="mb-7 flex flex-col items-center text-center">
            <Lambang ukuran="besar" />
            <h2 className="mt-5 text-[28px] font-semibold tracking-tight text-terang">
              Ada yang ingin Anda tanyakan?
            </h2>
            <p className="mt-2 text-sm text-redup">
              Mencari di dokumen, membaca gambar, atau mengambil data dari
              database — Agent memilih sendiri caranya.
            </p>
          </div>

          {kolom}

          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {CONTOH.map((contoh) => (
              <button
                key={contoh.teks}
                onClick={() => kirim(contoh.teks)}
                title={contoh.teks}
                className="flex items-center gap-2 rounded-full border border-garis bg-panel px-3.5 py-2 text-[13px] text-sedang transition hover:border-garis2 hover:bg-naik hover:text-terang"
              >
                <contoh.Ikon ukuran={15} />
                {contoh.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="scroll-halus flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6 sm:px-6">
          {memuatRiwayat && (
            <div className="flex justify-center pt-10">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-garis border-t-sedang" />
            </div>
          )}

          {pesan.map((m) =>
            m.role === 'system' && !m.error ? (
              <p
                key={m.id}
                className="animate-muncul mx-auto flex w-fit max-w-xl items-center gap-2 rounded-full border border-garis bg-naik px-3.5 py-1.5 text-xs text-sedang"
              >
                <IkonCentang ukuran={13} />
                {m.content}
              </p>
            ) : (
              <MessageBubble key={m.id} message={m} />
            ),
          )}

          {menunggu && (
            <div className="animate-muncul flex items-center gap-2.5 text-sm text-redup">
              <span className="flex gap-1">
                {[0, 150, 300].map((jeda) => (
                  <span
                    key={jeda}
                    style={{ animationDelay: `${jeda}ms` }}
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-sedang"
                  />
                ))}
              </span>
              Agent sedang bekerja…
            </div>
          )}

          <div ref={ujungRef} />
        </div>
      </div>

      {/* Bilah bawah tidak diberi garis pemisah maupun latar sendiri:
          kolomnya sudah punya batas sendiri, dan menumpuk keduanya membuat
          dasar layar terasa berat. */}
      <div className="shrink-0 px-4 pb-3 sm:px-6">
        <div className="mx-auto w-full max-w-3xl">
          {kolom}
          <p className="mt-2 text-center text-[11px] text-redup">
            <kbd className="rounded border border-garis bg-naik px-1 font-sans text-[10px]">
              Enter
            </kbd>{' '}
            mengirim,{' '}
            <kbd className="rounded border border-garis bg-naik px-1 font-sans text-[10px]">
              Shift+Enter
            </kbd>{' '}
            baris baru · Jawaban disusun model lokal — periksa kembali angka
            dan tanggal.
          </p>
        </div>
      </div>
    </div>
  )
}
