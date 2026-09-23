/**
 * Penyisipan dan pembacaan kembali rujukan berkas pada pertanyaan.
 *
 * Model tidak melihat antarmuka — ia hanya menerima teks — sehingga
 * "dokumen ini" tidak punya arti baginya dan nama berkas harus ikut
 * terkirim (pelajaran B-29). Tetapi pengguna tidak perlu melihat sisipan
 * itu: yang ia tulis "apa isi file ini", dan itu yang semestinya tampil.
 *
 * Penyisip dan pembacanya sengaja diletakkan berdampingan di satu berkas.
 * Keduanya harus memakai bentuk yang sama persis; bila salah satu diubah
 * sendirian, kartu lampiran berhenti muncul tanpa ada galat apa pun —
 * kegagalan diam yang paling mahal dicari.
 */

const BENTUK = [
  { jenis: 'dokumen', awalan: 'Menurut dokumen ', pemisah: ', ' },
  { jenis: 'gambar', awalan: 'Pada gambar ', pemisah: ', ' },
]

/** Sisipkan nama berkas ke pertanyaan, bila pengguna belum menyebutnya. */
export function lengkapiPertanyaan(teks, lampiran) {
  if (!lampiran || lampiran.status !== 'siap') return teks
  if (teks.toLowerCase().includes(lampiran.nama.toLowerCase())) return teks

  const bentuk = BENTUK.find((b) => b.jenis === lampiran.jenis) ?? BENTUK[0]
  return `${bentuk.awalan}${lampiran.nama}${bentuk.pemisah}${teks}`
}

/**
 * Pisahkan kembali rujukan berkas dari pertanyaannya.
 *
 * Dipakai saat menampilkan pesan pengguna — baik yang baru dikirim maupun
 * yang dimuat ulang dari riwayat. Karena yang dibaca adalah teks yang
 * tersimpan, tampilannya sama persis pada keduanya; tidak ada keadaan
 * tambahan yang harus ikut disimpan, dan tidak ada kolom baru di database.
 */
export function pisahLampiran(isi) {
  if (typeof isi !== 'string') return { lampiran: null, teks: isi }

  for (const { jenis, awalan, pemisah } of BENTUK) {
    if (!isi.startsWith(awalan)) continue
    const sisa = isi.slice(awalan.length)
    const batas = sisa.indexOf(pemisah)
    // Nama berkas yang kosong bukan sisipan kita — biarkan apa adanya.
    if (batas <= 0) continue
    return {
      lampiran: { nama: sisa.slice(0, batas), jenis },
      teks: sisa.slice(batas + pemisah.length),
    }
  }

  return { lampiran: null, teks: isi }
}
