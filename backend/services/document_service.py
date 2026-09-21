"""Pipeline dokumen: validasi berkas, ekstraksi teks, chunking, embedding,
penyimpanan, dan pencarian kemiripan (PRD §9 dan §18).
"""

from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Document
from backend.services.embedding_service import embed_query, embed_texts

logger = logging.getLogger(__name__)

try:  # libmagic tersedia di image backend, belum tentu di host.
    import magic  # type: ignore
except (ImportError, OSError) as exc:  # pragma: no cover - bergantung lingkungan
    magic = None  # type: ignore[assignment]
    logger.warning(
        "python-magic/libmagic tidak tersedia (%s). Pemeriksaan MIME type "
        "dilewati; pemeriksaan ekstensi, ukuran, dan signature tetap jalan.",
        exc,
    )

# Signature (magic bytes) tiap format yang diterima. Pemeriksaan ini menangkap
# berkas yang ekstensinya dipalsukan (PRD §18 - File Upload Security).
FILE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),  # byte 8-12 diperiksa terpisah, lihat _check_signature
}

# MIME yang sah untuk tiap ekstensi.
ALLOWED_MIME_TYPES: dict[str, tuple[str, ...]] = {
    ".pdf": ("application/pdf",),
    ".txt": ("text/plain",),
    ".md": ("text/plain", "text/markdown"),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
    ".webp": ("image/webp",),
}

TEXT_EXTENSIONS = (".txt", ".md")


class UploadValidationError(ValueError):
    """Berkas unggahan ditolak."""


class DocumentProcessingError(RuntimeError):
    """Berkas diterima tetapi isinya gagal diolah."""


@dataclass
class RetrievedChunk:
    """Satu potongan dokumen hasil pencarian kemiripan."""

    id: int
    filename: str
    content: str
    score: float
    metadata: dict[str, Any]


# --------------------------------------------------------------------------
# Validasi unggahan (PRD §18)
# --------------------------------------------------------------------------


def _extension_of(filename: str) -> str:
    return Path(filename).suffix.lower()


def _check_signature(extension: str, head: bytes) -> None:
    signatures = FILE_SIGNATURES.get(extension)
    if signatures is None:
        return  # .txt dan .md tidak punya signature; diperiksa sebagai teks.

    if not any(head.startswith(signature) for signature in signatures):
        raise UploadValidationError(
            f"Isi berkas tidak cocok dengan ekstensi {extension}."
        )

    # WEBP diawali "RIFF" sama seperti WAV dan AVI, jadi penanda formatnya
    # yang ada pada byte ke-8 sampai ke-12 ikut diperiksa.
    if extension == ".webp" and head[8:12] != b"WEBP":
        raise UploadValidationError("Berkas RIFF ini bukan gambar WEBP.")


def validate_upload(filename: str, head: bytes) -> str:
    """Periksa ekstensi, signature, dan MIME type dari beberapa kilobyte awal.

    Dipanggil sebelum berkas ditulis ke disk, sehingga unggahan yang ditolak
    tidak pernah tersimpan. Batas ukuran ditegakkan terpisah di `save_upload`,
    yang membaca bertahap dan berhenti begitu batas terlampaui.

    Mengembalikan ekstensi yang sudah dinormalisasi bila berkas diterima.
    """
    extension = _extension_of(filename)

    if extension not in settings.allowed_extensions:
        raise UploadValidationError(
            f"Ekstensi '{extension or '(kosong)'}' tidak diizinkan. "
            f"Yang diterima: {', '.join(settings.allowed_extensions)}."
        )

    if not head:
        raise UploadValidationError("Berkas kosong.")

    _check_signature(extension, head)

    if extension in TEXT_EXTENSIONS:
        try:
            head.decode("utf-8")
        except UnicodeDecodeError as exc:
            # Pemotongan `head` bisa membelah karakter multibyte di ujungnya,
            # jadi hanya galat yang jauh dari ujung yang dianggap nyata.
            if exc.start < len(head) - 4:
                raise UploadValidationError(
                    f"Berkas {extension} bukan teks UTF-8 yang sah."
                ) from exc

    if magic is not None:
        detected = magic.from_buffer(head, mime=True)
        if detected not in ALLOWED_MIME_TYPES.get(extension, ()):
            raise UploadValidationError(
                f"MIME type '{detected}' tidak cocok untuk ekstensi {extension}."
            )

    return extension


def save_upload(source: BinaryIO, filename: str) -> tuple[Path, int]:
    """Simpan unggahan ke storage/uploads sambil menegakkan batas ukuran.

    Berkas dibaca bertahap agar unggahan raksasa tidak pernah masuk memori
    utuh, dan dihapus lagi bila melewati batas. Nama berkas diganti dengan
    UUID supaya path traversal dan tabrakan nama tidak mungkin terjadi;
    nama asli tetap disimpan di kolom metadata.
    """
    extension = _extension_of(filename)
    destination_dir = Path(settings.upload_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{uuid.uuid4().hex}{extension}"

    limit = settings.max_upload_size_bytes
    size = 0
    try:
        with destination.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise UploadValidationError(
                        f"Ukuran berkas melebihi batas "
                        f"{settings.max_upload_size_mb} MB."
                    )
                target.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return destination, size


# --------------------------------------------------------------------------
# Ekstraksi teks dan chunking (PRD §9)
# --------------------------------------------------------------------------


def extract_text(path: Path, extension: str) -> str:
    """Ambil teks dari berkas. Gambar ditangani OCR Tool pada Fase 5."""
    if extension == ".pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise DocumentProcessingError(f"PDF gagal dibaca: {exc}") from exc

        text = "\n\n".join(pages)
        if not text.strip():
            raise DocumentProcessingError(
                "PDF tidak memuat teks yang dapat dibaca. Kemungkinan hasil "
                "pindaian — tunggu OCR Tool pada Fase 5."
            )
        return text

    if extension in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="replace")

    raise DocumentProcessingError(
        f"Ekstensi {extension} belum didukung pipeline dokumen."
    )


def clean_text(text: str) -> str:
    """Rapikan teks mentah sebelum dipotong.

    Spasi berlebih dan baris kosong beruntun dari hasil ekstraksi PDF membuat
    potongan terisi karakter kosong, sehingga jatah konteks terbuang.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str) -> list[str]:
    """Potong teks mengikuti CHUNK_SIZE dan CHUNK_OVERLAP di .env."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    return [chunk for chunk in splitter.split_text(text) if chunk.strip()]


# --------------------------------------------------------------------------
# Penyimpanan dan pencarian
# --------------------------------------------------------------------------


async def ingest_document(
    db: Session,
    *,
    original_filename: str,
    stored_path: Path,
    extension: str,
) -> int:
    """Olah satu berkas menjadi baris-baris `documents` yang siap dicari.

    Mengembalikan jumlah potongan yang tersimpan.
    """
    text = clean_text(extract_text(stored_path, extension))
    if not text:
        raise DocumentProcessingError("Berkas tidak memuat teks apa pun.")

    chunks = chunk_text(text)
    if not chunks:
        raise DocumentProcessingError("Teks gagal dipotong menjadi chunk.")

    vectors = await embed_texts(chunks)

    # Unggahan ulang dengan nama sama menggantikan isi lama, bukan
    # menumpuknya, agar hasil pencarian tidak berisi versi kedaluwarsa.
    db.execute(delete(Document).where(Document.filename == original_filename))

    db.add_all(
        [
            Document(
                filename=original_filename,
                content=chunk,
                embedding=vector,
                doc_metadata={
                    "chunk_index": index,
                    "chunk_total": len(chunks),
                    "source_path": str(stored_path),
                    "extension": extension,
                    "embedding_model": settings.embedding_model_name,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
    )
    db.commit()

    logger.info("Dokumen '%s' tersimpan sebagai %d chunk.", original_filename, len(chunks))
    return len(chunks)


def filter_relevant(
    chunks: list[RetrievedChunk],
    min_score_ratio: float | None = None,
) -> list[RetrievedChunk]:
    """Buang potongan yang jauh kalah relevan dibanding potongan terbaik.

    Pencarian kemiripan selalu mengembalikan sebanyak `top_k` baris, termasuk
    yang sama sekali tidak nyambung — pada uji Fase 3 ada potongan berskor 0
    yang tetap ikut terkirim. Potongan begitu memakan jatah konteks dan bisa
    mengalihkan perhatian model.

    Ambangnya relatif terhadap skor tertinggi, bukan angka mati, karena tiap
    model embedding punya rentang skor sendiri: ambang yang pas untuk satu
    model akan membuang semua hasil pada model lain. Potongan teratas selalu
    dipertahankan agar penyaringan ini tidak pernah mengosongkan konteks.
    """
    if not chunks:
        return []

    ratio = settings.rag_min_score_ratio if min_score_ratio is None else min_score_ratio
    if ratio <= 0:
        return chunks

    ambang = chunks[0].score * ratio
    disaring = [chunks[0]] + [
        chunk for chunk in chunks[1:] if chunk.score > 0 and chunk.score >= ambang
    ]

    if len(disaring) < len(chunks):
        logger.info(
            "Retrieval: %d dari %d potongan dipakai (ambang skor %.4f).",
            len(disaring), len(chunks), ambang,
        )
    return disaring


async def search_similar_chunks(
    db: Session,
    query: str,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Cari potongan dokumen paling mirip dengan pertanyaan (PRD §9).

    `score` adalah kemiripan cosine dalam rentang 0..1; makin besar makin
    mirip. pgvector mengembalikan jaraknya, jadi nilainya dibalik di sini.
    """
    limit = top_k or settings.rag_top_k
    query_vector = await embed_query(query)

    distance = Document.embedding.cosine_distance(query_vector).label("distance")
    rows = db.execute(
        select(Document, distance)
        .where(Document.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    ).all()

    return [
        RetrievedChunk(
            id=document.id,
            filename=document.filename,
            content=document.content,
            score=round(1.0 - float(dist), 4),
            metadata=document.doc_metadata or {},
        )
        for document, dist in rows
    ]
