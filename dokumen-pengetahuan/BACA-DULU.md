# Dokumen pengetahuan umum Kabupaten Hulu Sungai Selatan

Tiga PDF di folder ini dipakai sebagai basis pengetahuan asisten:

| Berkas | Isi |
|--------|-----|
| `01-profil-hulu-sungai-selatan.pdf` | Identitas, bentang alam, sebelas kecamatan, latar sejarah |
| `02-pariwisata-loksado-meratus.pdf` | Loksado, balanting paring, air terjun, Dayak Meratus |
| `03-kuliner-kerajinan-hss.pdf` | Ketupat Kandangan, dodol, pandai besi Nagara, kerbau rawa |

Sumber HTML-nya ada di `sumber/`. Untuk membuat ulang PDF setelah menyunting:

```bash
cd dokumen-pengetahuan/sumber
soffice --headless --convert-to pdf --outdir .. *.html
```

Lalu unggah ulang lewat tombol lampiran di antarmuka, atau:

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -X POST localhost:8000/upload -H "Authorization: Bearer $TOKEN" \
  -F "file=@01-profil-hulu-sungai-selatan.pdf"
```

Mengunggah berkas dengan nama sama akan **mengganti**, bukan menumpuk.

---

## Yang harus diperiksa sebelum dipakai untuk keperluan resmi

Isi dokumen ini **pengetahuan umum yang belum diverifikasi** terhadap sumber
resmi. Yang paling perlu dicocokkan:

- **Daftar dan jumlah kecamatan.** Ditulis sebelas; pemekaran wilayah dapat
  mengubahnya.
- **Latar sejarah Kerajaan Negara Daha** dan kaitannya dengan Kesultanan Banjar.
- **Nama-nama air terjun** di Loksado.
- **Rincian adat** Dayak Meratus, termasuk penyebutan balai dan Aruh Ganal.

## Mengapa tidak ada satu pun angka statistik

Ini disengaja, bukan kelalaian.

Sistem ini menjawab dengan mengutip dokumen dan menyebut nama berkasnya. Bila
sebuah angka dikarang lalu diindeks, asisten akan menyebutkannya **dengan yakin
dan tampak bersumber** — persis pola kegagalan yang tercatat sebagai B-29 di
`docs/bug-log.md`: jawaban yang terdengar meyakinkan justru karena bentuknya
benar, padahal isinya salah.

Karena itu setiap tempat yang seharusnya memuat angka ditandai
`[perlu data resmi BPS/Pemda]`. Penanda itu ikut terbaca asisten, sehingga
kekosongannya tersampaikan alih-alih terisi karangan.

Perilaku ini sudah diuji terhadap sistem yang berjalan:

> **Tanya:** Menurut dokumen, berapa jumlah penduduk Kabupaten Hulu Sungai Selatan?
> **Jawab:** Dokumen yang Anda unggah tidak menyediakan jumlah penduduk
> Kabupaten Hulu Sungai Selatan. Data tersebut belum ada di dokumen.

Saat data resmi tersedia, ganti penanda itu dengan angkanya **beserta tahun dan
sumbernya** — misalnya "234.000 jiwa (BPS, Sensus Penduduk 2020)" — supaya
jawaban asisten ikut menyebut dari mana angka itu berasal dan kapan berlakunya.
