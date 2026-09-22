/**
 * Menu pemilih model percakapan.
 *
 * Diletakkan di dalam kolom pertanyaan, bukan di header: model dipilih
 * per permintaan, jadi tempatnya memang di sebelah tempat permintaan itu
 * disusun — dan itu pula letaknya pada Grok.
 *
 * Daftarnya dibaca dari `/models`, yang membacanya langsung dari Ollama.
 * Jadi `ollama pull` cukup untuk menambah pilihan; tidak ada daftar salinan
 * di sisi antarmuka yang bisa menua tanpa disadari.
 */
import { useEffect, useRef, useState } from 'react'
import { daftarModel } from '../services/api'
import { IkonCentang, IkonPanahKanan } from './Ikon'

/**
 * Pendekkan nama model untuk pil yang sempit.
 *
 * `qwen2.5:3b-instruct-q4_K_M` menjadi `qwen2.5:3b`. Tingkat kuantisasi dan
 * varian instruct jarang jadi pembeda yang dicari sekilas, sedangkan nama
 * penuhnya tetap ada di daftar dan pada atribut `title`.
 */
function namaPendek(nama) {
  const [dasar, tag] = nama.split(':')
  if (!tag) return dasar
  return `${dasar}:${tag.split('-')[0]}`
}

export default function PemilihModel({ nilai, onPilih, nonaktif }) {
  const [model, setModel] = useState([])
  const [bawaan, setBawaan] = useState(null)
  const [galat, setGalat] = useState(null)
  const [buka, setBuka] = useState(false)
  const wadahRef = useRef(null)
  // Nilai tersimpan saat komponen dipasang, dipakai sekali untuk memeriksa
  // apakah model itu masih ada.
  const nilaiAwal = useRef(nilai)

  useEffect(() => {
    let batal = false
    daftarModel()
      .then((d) => {
        if (batal) return
        setModel(d.models)
        setBawaan(d.default)
        setGalat(null)
        // Model yang tersimpan bisa saja sudah dihapus dengan `ollama rm`
        // sejak terakhir dipakai. Pilihannya dilepas di sini, saat daftar
        // yang sebenarnya baru diketahui. Tanpa langkah ini pil menampilkan
        // model bawaan sementara yang dikirim tetap nama lama — dan
        // permintaannya ditolak backend dengan 400.
        if (nilaiAwal.current && !d.models.includes(nilaiAwal.current)) {
          onPilih(null)
        }
      })
      .catch((e) => !batal && setGalat(e.message))
    return () => {
      batal = true
    }
    // Sengaja hanya berjalan sekali saat dipasang: yang diperiksa adalah
    // nilai tersimpan, bukan setiap perubahan pilihan sesudahnya.
  }, [onPilih])

  useEffect(() => {
    if (!buka) return
    const tutup = (e) => e.key === 'Escape' && setBuka(false)
    const klikLuar = (e) => {
      if (!wadahRef.current?.contains(e.target)) setBuka(false)
    }
    window.addEventListener('keydown', tutup)
    document.addEventListener('mousedown', klikLuar)
    return () => {
      window.removeEventListener('keydown', tutup)
      document.removeEventListener('mousedown', klikLuar)
    }
  }, [buka])

  // Yang ditampilkan selalu model yang benar-benar akan dipakai backend:
  // pilihan pengguna bila masih ada, selain itu model bawaan.
  const aktif = nilai && model.includes(nilai) ? nilai : bawaan

  if (galat) return null

  return (
    <div ref={wadahRef} className="relative">
      <button
        type="button"
        disabled={nonaktif || !aktif}
        onClick={() => setBuka((b) => !b)}
        title={aktif ? `Model: ${aktif}` : 'Memuat daftar model…'}
        aria-haspopup="listbox"
        aria-expanded={buka}
        className="flex max-w-[11rem] items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs font-medium text-sedang transition hover:bg-naik2 hover:text-terang disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span className="truncate">
          {aktif ? namaPendek(aktif) : 'Memuat…'}
        </span>
        <IkonPanahKanan
          ukuran={12}
          className={`transition ${buka ? '-rotate-90' : 'rotate-90'}`}
        />
      </button>

      {buka && (
        <div
          role="listbox"
          className="animate-naik absolute bottom-10 left-0 z-30 w-72 overflow-hidden rounded-xl border border-garis bg-panel p-1 shadow-2xl shadow-black/50"
        >
          <p className="px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-redup">
            Model percakapan
          </p>
          {model.map((m) => {
            const dipilih = m === aktif
            return (
              <button
                key={m}
                type="button"
                role="option"
                aria-selected={dipilih}
                onClick={() => {
                  // Memilih model bawaan disimpan sebagai `null`, bukan
                  // namanya: dengan begitu mengubah OLLAMA_LLM_MODEL di
                  // `.env` langsung berlaku, tidak tertahan oleh pilihan
                  // lama yang mengendap di peramban.
                  onPilih(m === bawaan ? null : m)
                  setBuka(false)
                }}
                className="flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left transition hover:bg-naik"
              >
                <span className="mt-0.5 w-3.5 shrink-0 text-terang">
                  {dipilih && <IkonCentang ukuran={13} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] text-terang">{m}</span>
                  {m === bawaan && (
                    <span className="mt-0.5 block text-[11px] text-redup">
                      bawaan dari .env
                    </span>
                  )}
                </span>
              </button>
            )
          })}
          <p className="mt-1 border-t border-garis px-2.5 pb-1 pt-2 text-[11px] leading-relaxed text-redup">
            Semua dijalankan lokal oleh Ollama. Tambah pilihan dengan
            <code className="ml-1 rounded bg-naik px-1">ollama pull</code>.
          </p>
        </div>
      )}
    </div>
  )
}
