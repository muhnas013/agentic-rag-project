/**
 * Kartu berkas yang sedang dilampirkan, tampil di atas kolom pertanyaan.
 *
 * Berkas diunggah **begitu dipilih**, bukan menunggu pertanyaan dikirim.
 * Mengindeks PDF memakan waktu beberapa detik, dan mengerjakannya selagi
 * pengguna mengetik membuat waktu itu tidak terasa. Kartunya memperlihatkan
 * kemajuan sekaligus hasilnya, sehingga pengguna tahu kapan berkasnya siap
 * ditanyai.
 */
import { IkonBerkas, IkonGambar, IkonSilang } from './Ikon'

/** Label jenis singkat, seperti "PDF" atau "Gambar JPG". */
function label(nama, jenis) {
  const ekst = (nama.split('.').pop() || '').toUpperCase()
  return jenis === 'gambar' ? `Gambar ${ekst}` : ekst || 'Dokumen'
}

export default function KartuLampiran({ lampiran, onLepas }) {
  if (!lampiran) return null

  const { nama, jenis, status, progres, potongan, galat } = lampiran
  const Ikon = jenis === 'gambar' ? IkonGambar : IkonBerkas

  const keterangan =
    status === 'mengunggah'
      ? `Mengunggah… ${progres}%`
      : status === 'gagal'
        ? galat
        : jenis === 'gambar'
          ? `${label(nama, jenis)} · dibaca saat ditanyakan`
          : `${label(nama, jenis)} · ${potongan} potongan terindeks`

  return (
    <div className="mb-2 flex items-center gap-2.5 rounded-2xl border border-garis bg-panel px-3 py-2.5">
      <span
        aria-hidden
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
          status === 'gagal' ? 'bg-rose-950/40 text-rose-300' : 'bg-naik2 text-sedang'
        }`}
      >
        {status === 'mengunggah' ? (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-garis2 border-t-terang" />
        ) : (
          <Ikon ukuran={17} />
        )}
      </span>

      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] font-medium text-terang">
          {nama}
        </span>
        <span
          className={`mt-0.5 block truncate text-[11px] ${
            status === 'gagal' ? 'text-rose-300' : 'text-redup'
          }`}
        >
          {keterangan}
        </span>
      </span>

      <button
        type="button"
        onClick={onLepas}
        title="Lepas lampiran"
        aria-label={`Lepas lampiran ${nama}`}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-redup transition hover:bg-naik2 hover:text-terang"
      >
        <IkonSilang ukuran={14} />
      </button>
    </div>
  )
}
