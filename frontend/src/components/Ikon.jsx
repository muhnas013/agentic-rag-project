/**
 * Ikon garis, digambar sebagai SVG sebaris.
 *
 * Menggantikan emoji yang dipakai sebelumnya. Emoji dirender oleh berkas
 * font sistem, jadi bentuk dan warnanya berbeda-beda di tiap mesin dan
 * selalu berwarna penuh — pada tema gelap yang nyaris tanpa warna, itu
 * satu-satunya hal yang paling merusak kesan rapi.
 *
 * Ditulis sendiri, bukan memasang pustaka ikon: yang dipakai hanya belasan
 * bentuk, sedangkan satu pustaka membawa ribuan.
 *
 * Semua memakai `currentColor`, sehingga warnanya mengikuti kelas teks
 * induknya dan tidak perlu diatur dua kali.
 */

function Svg({ anak, ukuran = 16, className = '', isi = 'none' }) {
  return (
    <svg
      aria-hidden
      xmlns="http://www.w3.org/2000/svg"
      width={ukuran}
      height={ukuran}
      viewBox="0 0 24 24"
      fill={isi}
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`shrink-0 ${className}`}
    >
      {anak}
    </svg>
  )
}

export const IkonDokumen = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
      </>
    }
  />
)

export const IkonRoda = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    }
  />
)

export const IkonKeluar = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <path d="m16 17 5-5-5-5" />
        <path d="M21 12H9" />
      </>
    }
  />
)

export const IkonKlip = (p) => (
  <Svg
    {...p}
    anak={
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    }
  />
)

export const IkonPanahAtas = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <path d="M12 19V5" />
        <path d="m5 12 7-7 7 7" />
      </>
    }
  />
)

export const IkonTambah = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <path d="M5 12h14" />
        <path d="M12 5v14" />
      </>
    }
  />
)

export const IkonSilang = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <path d="M18 6 6 18" />
        <path d="m6 6 12 12" />
      </>
    }
  />
)

export const IkonPanahKanan = (p) => <Svg {...p} anak={<path d="m9 18 6-6-6-6" />} />

export const IkonCentang = (p) => <Svg {...p} anak={<path d="M20 6 9 17l-5-5" />} />

export const IkonPeringatan = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
      </>
    }
  />
)

export const IkonBerkas = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
        <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        <path d="M16 13H8" />
        <path d="M16 17H8" />
      </>
    }
  />
)

export const IkonGambar = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="9" cy="9" r="1.75" />
        <path d="m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21" />
      </>
    }
  />
)

export const IkonBasisData = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
      </>
    }
  />
)

export const IkonCari = (p) => (
  <Svg
    {...p}
    anak={
      <>
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </>
    }
  />
)

/**
 * Lambang aplikasi. Bentuknya dipakai juga sebagai avatar jawaban asisten,
 * jadi harus tetap terbaca pada ukuran 16px.
 */
export const IkonMerek = ({ ukuran = 18, className = '' }) => (
  <svg
    aria-hidden
    xmlns="http://www.w3.org/2000/svg"
    width={ukuran}
    height={ukuran}
    viewBox="0 0 24 24"
    fill="none"
    className={`shrink-0 ${className}`}
  >
    <path d="M12 2 22 12 12 22 2 12Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
    <path d="M12 7.5 16.5 12 12 16.5 7.5 12Z" fill="currentColor" />
  </svg>
)
