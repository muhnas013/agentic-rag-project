/**
 * Cetak laporan HTML menjadi PDF memakai Chromium.
 *
 * LibreOffice dipakai lebih dulu dan tidak memadai untuk laporan ini:
 * ia mengabaikan lebar gambar dari HTML maupun CSS, dan mengabaikan pula
 * resolusi cetak yang ditanam di dalam berkas PNG (chunk pHYs) — gambar
 * selalu disisipkan pada ukuran piksel dibagi 96 dpi, sehingga tangkapan
 * layar selebar 1280 px meluber jauh melewati batas halaman. Satu-satunya
 * jalan keluar di sana adalah memperkecil berkas gambarnya, yang berarti
 * mengorbankan ketajaman cetak.
 *
 * Chromium mencetak dari mesin render yang sama dengan peramban, sehingga
 * lebar gambar, garis tabel, dan pemenggalan halaman berlaku sebagaimana
 * ditulis di CSS — dan gambar tetap disematkan pada resolusi penuh.
 *
 * Pemakaian:
 *   mise x "npm:playwright" -- node bangun-laporan.mjs <masukan.html> <keluaran.pdf>
 */
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import { chromium } from '/home/nzrl4h/.local/share/mise/installs/npm-playwright/1.63.0/node_modules/playwright/index.mjs'

const [masukan, keluaran] = process.argv.slice(2)
if (!masukan || !keluaran) {
  console.error('Pemakaian: node bangun-laporan.mjs <masukan.html> <keluaran.pdf>')
  process.exit(1)
}

const b = await chromium.launch({ executablePath: '/usr/bin/chromium' })
const hal = await b.newPage()

// Dimuat lewat file:// supaya path gambar yang relatif tetap terselesaikan.
await hal.goto(pathToFileURL(path.resolve(masukan)).href, { waitUntil: 'networkidle' })

// Tanpa ini, latar tabel dan kotak catatan hilang saat dicetak — peramban
// membuangnya secara bawaan demi menghemat tinta.
await hal.pdf({
  path: path.resolve(keluaran),
  format: 'A4',
  printBackground: true,
  margin: { top: '2.2cm', bottom: '2cm', left: '2.2cm', right: '2.2cm' },
})

await b.close()
console.log('PDF dibuat:', keluaran)
