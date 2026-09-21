"""Tool 2 — Image OCR (PRD §8 dan §10).

Pipeline PRD §10: unggah gambar → validasi → PaddleOCR → teks → Agent → jawaban.
Validasi berkasnya sudah dikerjakan `document_service` saat unggahan masuk;
modul ini menangani dua langkah berikutnya.

PaddleOCR berjalan di CPU (`OCR_USE_GPU=false`, keputusan D-02) agar tidak
berebut VRAM dengan LLM. Dengan 24 thread, OCR di CPU masih cepat.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from backend.config import settings
from backend.services.document_service import sanitise_filename
from backend.tools import ToolInvocation, record

logger = logging.getLogger(__name__)

# Baris dengan keyakinan di bawah ini disaring: hasil OCR yang meleset lebih
# berbahaya daripada baris yang hilang, karena model tidak punya cara tahu
# bahwa angka yang dibacanya salah.
AMBANG_KEYAKINAN = 0.5

_ocr: Any = None
_kunci = threading.Lock()


def _muat_ocr() -> Any:
    """Siapkan PaddleOCR sekali saja, lalu pakai ulang.

    Inisialisasinya memuat model deteksi dan pengenalan ke memori — mahal
    bila diulang tiap permintaan. Kunci dipasang karena tool bisa dipanggil
    dari beberapa permintaan sekaligus.
    """
    global _ocr
    if _ocr is not None:
        return _ocr

    with _kunci:
        if _ocr is not None:  # sudah disiapkan thread lain saat menunggu
            return _ocr

        from paddleocr import PaddleOCR

        logger.info("Menyiapkan PaddleOCR (lang=%s, GPU=%s)...",
                    settings.ocr_lang, settings.ocr_use_gpu)
        _ocr = PaddleOCR(
            lang=settings.ocr_lang,
            device="gpu" if settings.ocr_use_gpu else "cpu",
            # oneDNN dimatikan: paddlepaddle 3.3.1 gagal pada eksekutor PIR
            # dengan galat ConvertPirAttribute2RuntimeAttribute. Tanpa oneDNN
            # hasilnya benar, hanya sedikit lebih lambat.
            enable_mkldnn=False,
            # Tiga praproses ini untuk foto dokumen yang miring atau
            # melengkung. Dimatikan karena memperlambat tanpa memberi
            # manfaat pada gambar tegak, dan bisa dihidupkan bila perlu.
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        logger.info("PaddleOCR siap.")
        return _ocr


def ocr_tersedia() -> bool:
    """Apakah PaddleOCR bisa dipakai di lingkungan ini?"""
    try:
        import paddleocr  # noqa: F401
    except Exception as exc:  # pragma: no cover - bergantung lingkungan
        logger.warning("PaddleOCR tidak tersedia: %s", exc)
        return False
    return True


def resolve_image_path(image_path: str) -> Path:
    """Temukan berkas gambar dari nama yang disebut pengguna.

    Pengguna menyebut "struk.png", sedangkan di disk berkasnya tersimpan
    sebagai `<uuid>__struk.png` (lihat `document_service.save_upload`).
    Fungsi ini menjembatani keduanya: nama persis dicoba lebih dulu, lalu
    dicari berkas yang berakhiran nama tersebut — yang terbaru bila ada
    beberapa unggahan dengan nama sama.

    Nama datang dari LLM, jadi diperlakukan sebagai masukan tidak tepercaya:
    komponen direktori dibuang, dan hasil akhirnya diperiksa apakah benar
    masih berada di bawah folder unggahan.
    """
    dasar = Path(settings.upload_dir).resolve()
    diminta = sanitise_filename(image_path)

    kandidat = (dasar / diminta).resolve()
    if not kandidat.is_relative_to(dasar):
        raise ValueError("Path gambar berada di luar folder unggahan.")

    if not kandidat.exists():
        cocok = sorted(
            dasar.glob(f"*__{diminta}"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not cocok:
            raise FileNotFoundError(f"Berkas '{diminta}' tidak ditemukan.")
        kandidat = cocok[0]

    if kandidat.suffix.lower() not in settings.allowed_image_extensions:
        raise ValueError(f"Berkas '{kandidat.suffix}' bukan gambar yang didukung.")

    return kandidat


def _kotak(poly: Any) -> tuple[float, float, float]:
    """Ambil (x_kiri, y_tengah, tinggi) dari satu kotak teks.

    Menerima dua bentuk yang dipakai PaddleOCR: poligon empat titik
    (`rec_polys`) maupun kotak sejajar sumbu `[x1, y1, x2, y2]` (`rec_boxes`).
    """
    titik = list(poly)
    if len(titik) == 4 and not hasattr(titik[0], "__len__"):
        x1, y1, x2, y2 = (float(v) for v in titik)
        return x1, (y1 + y2) / 2, abs(y2 - y1)

    xs = [float(t[0]) for t in titik]
    ys = [float(t[1]) for t in titik]
    return min(xs), (min(ys) + max(ys)) / 2, max(ys) - min(ys)


def susun_baris(teks: list[str], polys: list[Any]) -> list[str]:
    """Rangkai potongan teks kembali menjadi baris sesuai tata letaknya.

    PaddleOCR mengembalikan tiap kotak teks terpisah, sehingga "TOTAL" dan
    "366300" yang bersebelahan pada struk datang sebagai dua entri. Bila
    keduanya disambung dengan baris baru, kaitan label dan nilainya hilang —
    dan model lalu menjawab angka yang salah. Pada pengujian, "berapa total
    transaksi" dijawab dengan nilai "Tunai", bukan "TOTAL".

    Potongan yang pusat vertikalnya berdekatan digabung menjadi satu baris,
    diurutkan dari kiri ke kanan. Toleransinya mengikuti tinggi huruf, bukan
    angka mati, supaya tetap benar pada gambar beresolusi berbeda.
    """
    if not polys or len(polys) != len(teks):
        # Tanpa koordinat yang sepadan, urutan asli adalah tebakan terbaik.
        return [t for t in teks if t.strip()]

    butir = []
    for t, poly in zip(teks, polys):
        if not t.strip():
            continue
        x, y, tinggi = _kotak(poly)
        butir.append((y, x, t.strip(), tinggi))

    if not butir:
        return []

    butir.sort(key=lambda b: (b[0], b[1]))

    baris: list[list[tuple[float, str]]] = []
    y_acuan: list[float] = []
    for y, x, t, tinggi in butir:
        toleransi = max(tinggi * 0.6, 4.0)
        if baris and abs(y - y_acuan[-1]) <= toleransi:
            baris[-1].append((x, t))
        else:
            baris.append([(x, t)])
            y_acuan.append(y)

    return ["  ".join(t for _, t in sorted(kel)) for kel in baris]


def baca_teks(berkas: Path) -> tuple[list[str], float]:
    """Jalankan OCR, kembalikan baris teks dan keyakinan terendahnya.

    Memanggil PaddleOCR secara langsung (memblokir); pemanggil dari konteks
    async harus membungkusnya dengan `asyncio.to_thread`.
    """
    hasil = _muat_ocr().predict(str(berkas))
    if not hasil:
        return [], 0.0

    r = hasil[0]
    teks = r.get("rec_texts") or []
    skor = r.get("rec_scores") or []
    polys = r.get("rec_polys") or r.get("rec_boxes") or r.get("dt_polys") or []

    # Baris yang meragukan dibuang lebih dulu, berikut koordinatnya, agar
    # tidak ikut membentuk tata letak.
    simpan = [
        (t, s, p)
        for t, s, p in zip(teks, skor, polys or [None] * len(teks))
        if s >= AMBANG_KEYAKINAN and t.strip()
    ]
    dibuang = len(teks) - len(simpan)
    if dibuang:
        logger.info("OCR %s: %d potongan dibuang karena keyakinan rendah.",
                    berkas.name, dibuang)

    if not simpan:
        return [], 0.0

    baris = susun_baris(
        [t for t, _, _ in simpan],
        [p for _, _, p in simpan] if polys else [],
    )
    return baris, min(s for _, s, _ in simpan)


@tool("Image_OCR")
async def image_ocr(image_path: str) -> str:
    """Baca teks dari berkas gambar yang diunggah pengguna.

    Gunakan ketika pengguna bertanya mengenai isi sebuah gambar, foto,
    struk, atau hasil pindaian.

    Args:
        image_path: Nama berkas gambar yang sudah diunggah, misalnya "struk.png".
    """
    try:
        berkas = resolve_image_path(image_path)
    except (ValueError, FileNotFoundError) as exc:
        record(ToolInvocation("Image_OCR", ok=False, detail=str(exc)))
        return f"Gambar tidak dapat dibaca: {exc}"

    if not ocr_tersedia():
        record(ToolInvocation("Image_OCR", ok=False, detail="PaddleOCR tidak terpasang"))
        return (
            "Fitur OCR belum tersedia di lingkungan ini. Sampaikan kepada "
            "pengguna bahwa isi gambar belum bisa dibaca."
        )

    try:
        # OCR memakai CPU secara penuh dan memblokir; dijalankan di thread
        # terpisah agar event loop tetap melayani permintaan lain.
        baris, keyakinan = await asyncio.to_thread(baca_teks, berkas)
    except Exception as exc:
        logger.exception("OCR gagal untuk %s", berkas.name)
        record(ToolInvocation("Image_OCR", ok=False, detail=str(exc)))
        return f"Pembacaan gambar gagal: {exc}"

    if not baris:
        record(ToolInvocation("Image_OCR", ok=True, detail="tidak ada teks terbaca"))
        return (
            "Tidak ada teks yang terbaca pada gambar itu. Sampaikan kepada "
            "pengguna bahwa gambarnya mungkin buram atau tidak memuat tulisan."
        )

    record(ToolInvocation("Image_OCR", ok=True,
                          detail=f"{len(baris)} baris, keyakinan min {keyakinan:.2f}"))
    logger.info("OCR %s -> %d baris (keyakinan min %.2f)",
                berkas.name, len(baris), keyakinan)

    catatan = ""
    if keyakinan < 0.8:
        # Angka yang salah baca tidak bisa dideteksi model dari teksnya saja,
        # jadi ketidakpastiannya disampaikan eksplisit.
        catatan = ("\n\n(Catatan: sebagian teks terbaca kurang yakin. "
                   "Sebutkan kemungkinan salah baca bila mengutip angka.)")

    return (
        f"Teks hasil pembacaan gambar '{berkas.name}':\n\n"
        + "\n".join(baris)
        + catatan
    )
