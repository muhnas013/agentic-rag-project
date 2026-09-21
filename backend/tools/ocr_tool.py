"""Tool 2 — Image OCR (PRD §8 dan §10).

PaddleOCR dipasang pada Fase 5. Sampai saat itu tool ini tetap didaftarkan
ke Agent supaya perutean tool bisa diuji lebih dulu: Agent harus belajar
mengenali pertanyaan yang menyangkut gambar, terlepas dari apakah mesin
OCR-nya sudah ada. Yang dikembalikan adalah pesan jelas bahwa fiturnya
belum tersedia, bukan galat.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.tools import tool

from backend.config import settings
from backend.services.document_service import sanitise_filename
from backend.tools import ToolInvocation, record

logger = logging.getLogger(__name__)

OCR_SIAP = False  # diubah menjadi True pada Fase 5


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


@tool("Image_OCR")
def image_ocr(image_path: str) -> str:
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

    if not OCR_SIAP:
        pesan = (
            "Fitur OCR belum tersedia — PaddleOCR baru dipasang pada Fase 5. "
            "Sampaikan kepada pengguna bahwa isi gambar belum bisa dibaca."
        )
        record(ToolInvocation("Image_OCR", ok=False, detail="PaddleOCR belum dipasang"))
        logger.info("Image_OCR dipanggil untuk %s, tetapi OCR belum siap.", berkas.name)
        return pesan

    raise NotImplementedError("Diisi pada Fase 5.")  # pragma: no cover
