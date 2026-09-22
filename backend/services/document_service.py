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
from sqlalchemy import Text, cast, delete, func, literal_column, select
from sqlalchemy.dialects.postgresql import TSQUERY
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


def sanitise_filename(filename: str) -> str:
    """Jadikan nama berkas aman dipakai di disk.

    Komponen direktori dibuang lebih dulu, lalu karakter di luar huruf,
    angka, titik, garis bawah, dan strip diganti garis bawah. Dengan begitu
    "../../etc/passwd" menjadi "passwd" saja.
    """
    nama = Path(filename).name
    bersih = re.sub(r"[^A-Za-z0-9._-]", "_", nama).lstrip(".")
    return (bersih or "berkas")[:100]


def save_upload(source: BinaryIO, filename: str) -> tuple[Path, int]:
    """Simpan unggahan ke storage/uploads sambil menegakkan batas ukuran.

    Berkas dibaca bertahap agar unggahan raksasa tidak pernah masuk memori
    utuh, dan dihapus lagi bila melewati batas.

    Nama di disk berbentuk `<uuid>__<nama-asli-yang-dibersihkan>`. Awalan UUID
    menutup tabrakan nama antar pengguna dan membuat path traversal mustahil,
    sementara nama asli yang ikut disimpan membuat berkas masih bisa dicari
    kembali dari nama yang dikenal pengguna — itulah yang dibutuhkan Image_OCR,
    karena pengguna menyebut "struk.png", bukan UUID-nya.
    """
    destination_dir = Path(settings.upload_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{uuid.uuid4().hex}__{sanitise_filename(filename)}"

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
# Deteksi prompt injection (PRD §18)
# --------------------------------------------------------------------------

# Pola perintah yang berusaha mengambil alih peran model. Dicocokkan saat
# dokumen masuk, bukan saat pencarian: pemindaian cukup sekali per dokumen,
# dan hasilnya tersimpan sehingga tiap pencarian tidak perlu mengulanginya.
POLA_INJEKSI: tuple[tuple[str, str], ...] = (
    (r"abaikan\s+(semua\s+)?(instruksi|perintah|aturan)", "abaikan instruksi"),
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", "ignore instructions"),
    (r"(kamu|anda)\s+sekarang\s+(adalah|menjadi)", "penggantian peran"),
    (r"you\s+are\s+now\s+(a|an)\b", "role override"),
    (r"lupakan\s+(semua\s+)?(instruksi|aturan|peran)", "lupakan instruksi"),
    (r"jawab\s+setiap\s+pertanyaan\s+dengan", "paksa jawaban tetap"),
    (r"(tuliskan|tampilkan|bocorkan)\s+(ulang\s+)?(seluruh\s+)?(instruksi|prompt)\s+sistem", "minta bocorkan prompt"),
    (r"(reveal|print|repeat)\s+(your\s+)?(system\s+)?(prompt|instructions)", "reveal prompt"),
    (r"disregard\s+(all\s+)?(previous|prior)", "disregard"),
)

_POLA_TERKOMPILASI = tuple(
    (re.compile(pola, re.IGNORECASE), label) for pola, label in POLA_INJEKSI
)


def detect_injection(text: str) -> list[str]:
    """Kembalikan label pola pengambilalihan yang ditemukan di teks.

    Ini lapisan pertahanan, bukan jaminan — pola baru selalu bisa disusun.
    Gunanya menaikkan ambang serangan yang sudah dikenal, sejalan dengan
    cara SQL Tool memvalidasi query alih-alih memercayai model.
    """
    return [label for pola, label in _POLA_TERKOMPILASI if pola.search(text)]


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

    # Dokumen dipindai sekali di sini. Potongan yang memuat pola
    # pengambilalihan ditandai, lalu disingkirkan dari hasil pencarian
    # (lihat search_similar_chunks) sehingga tidak pernah sampai ke model.
    flags_per_chunk = [detect_injection(chunk) for chunk in chunks]
    tertandai = sum(1 for f in flags_per_chunk if f)
    if tertandai:
        logger.warning(
            "Dokumen '%s': %d dari %d potongan memuat pola prompt injection %s",
            original_filename, tertandai, len(chunks),
            sorted({l for f in flags_per_chunk for l in f}),
        )

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
                    "injection_flags": flags,
                },
            )
            for index, (chunk, vector, flags) in enumerate(
                zip(chunks, vectors, flags_per_chunk)
            )
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


def _kondisi_dasar() -> list:
    """Syarat yang berlaku untuk semua jalur pencarian."""
    kondisi = [Document.embedding.is_not(None)]
    if settings.rag_quarantine_suspicious:
        # Potongan yang ditandai saat masuk tidak pernah ikut hasil pencarian.
        # Disaring di SQL, bukan sesudahnya, supaya potongan bersih berikutnya
        # naik mengisi kuota.
        kondisi.append(
            func.coalesce(
                func.jsonb_array_length(Document.doc_metadata["injection_flags"]), 0
            )
            == 0
        )
    return kondisi


def _jadikan_potongan(document: Document, skor: float) -> RetrievedChunk:
    return RetrievedChunk(
        id=document.id,
        filename=document.filename,
        content=document.content,
        score=round(float(skor), 4),
        metadata=document.doc_metadata or {},
    )


async def search_vector(db: Session, query: str, limit: int) -> list[RetrievedChunk]:
    """Pencarian kemiripan makna lewat pgvector (PRD §9).

    `score` adalah kemiripan cosine 0..1; makin besar makin mirip. pgvector
    mengembalikan jaraknya, jadi nilainya dibalik di sini.
    """
    query_vector = await embed_query(query)
    distance = Document.embedding.cosine_distance(query_vector).label("distance")

    rows = db.execute(
        select(Document, distance)
        .where(*_kondisi_dasar())
        .order_by(distance)
        .limit(limit)
    ).all()

    return [_jadikan_potongan(d, 1.0 - float(dist)) for d, dist in rows]


def _tsquery_atau(query: str):
    """Susun tsquery yang mencocokkan sebagian kata, bukan seluruhnya.

    `plainto_tsquery` menggabungkan semua kata dengan AND, sehingga
    pertanyaan sewajarnya tidak pernah cocok: "berapa lama masa retensi
    dokumen kepegawaian" menuntut dokumen memuat "berapa" dan "lama" juga.
    Pada pengujian pertama, kekeliruan ini membuat jalur teks penuh
    mengembalikan kosong untuk **setiap** pertanyaan — dan karena
    penggabungan RRF tetap berjalan, hasilnya diam-diam sama persis dengan
    pencarian vektor saja. Tidak ada galat, hanya fitur yang tidak berbuat
    apa-apa.

    Operatornya diganti menjadi OR lewat penulisan ulang teks tsquery yang
    sudah dibersihkan `plainto_tsquery`, jadi masukan pengguna tidak pernah
    masuk ke tsquery mentah. Dokumen yang memuat lebih banyak kata tetap
    naik ke atas dengan sendirinya lewat `ts_rank`.
    """
    bahasa = settings.rag_fts_language
    return cast(
        func.replace(cast(func.plainto_tsquery(bahasa, query), Text), " & ", " | "),
        TSQUERY,
    )


def search_fulltext(db: Session, query: str, limit: int) -> list[RetrievedChunk]:
    """Pencarian teks penuh PostgreSQL (PRD §25 - Hybrid Search).

    Melengkapi pencarian vektor, bukan menggantikannya. Keduanya gagal pada
    hal yang berbeda: vektor meleset ketika istilahnya persis tetapi
    konteksnya asing, sedangkan teks penuh meleset ketika pertanyaannya
    parafrase. Pada bahasa Indonesia jalur ini justru lebih dapat diandalkan,
    karena konfigurasi `indonesian` PostgreSQL melakukan stemming sungguhan —
    "kepegawaian" dan "pegawai" sama-sama menjadi "gawai".
    """
    # Kolom dihitung PostgreSQL sendiri, jadi tidak ada padanannya di model.
    kolom_tsv = literal_column("content_tsv")
    tsquery = _tsquery_atau(query)
    peringkat = func.ts_rank(kolom_tsv, tsquery).label("peringkat")

    rows = db.execute(
        select(Document, peringkat)
        .where(*_kondisi_dasar(), kolom_tsv.op("@@")(tsquery))
        .order_by(peringkat.desc())
        .limit(limit)
    ).all()

    return [_jadikan_potongan(d, skor) for d, skor in rows]


def gabung_rrf(
    *peringkat: list[RetrievedChunk],
    bobot: tuple[float, ...] | None = None,
    k: int | None = None,
    limit: int = 4,
) -> list[RetrievedChunk]:
    """Gabungkan beberapa daftar hasil memakai Reciprocal Rank Fusion.

    Skor kedua jalur tidak sebanding — kemiripan cosine berkisar 0..1
    sementara `ts_rank` punya skala sendiri — sehingga menjumlahkannya
    langsung tidak bermakna. RRF hanya memakai **urutan**, bukan nilainya:
    tiap potongan mendapat 1/(k + peringkat) dari setiap daftar.

    Efeknya, potongan yang muncul di kedua daftar naik ke atas walau tidak
    menjuarai salah satunya — dan itulah yang dicari dari penggabungan ini.

    `bobot` memberi tiap daftar pengaruh berbeda. Itu diperlukan karena
    kedua jalur di sini tidak sama andalnya: pada pengujian, pencarian teks
    penuh benar 4 dari 5 sementara vektor hanya 2 dari 5, sehingga
    penggabungan berbobot sama justru menarik hasil yang benar ke bawah.
    """
    k = settings.rag_rrf_k if k is None else k
    if bobot is None:
        bobot = (1.0,) * len(peringkat)

    skor: dict[int, float] = {}
    asal: dict[int, RetrievedChunk] = {}

    for daftar, w in zip(peringkat, bobot):
        for urutan, potongan in enumerate(daftar, start=1):
            skor[potongan.id] = skor.get(potongan.id, 0.0) + w / (k + urutan)
            asal.setdefault(potongan.id, potongan)

    terbaik = sorted(skor.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [
        RetrievedChunk(
            id=asal[i].id,
            filename=asal[i].filename,
            content=asal[i].content,
            score=round(nilai, 5),
            metadata=asal[i].metadata,
        )
        for i, nilai in terbaik
    ]


async def search_similar_chunks(
    db: Session,
    query: str,
    top_k: int | None = None,
    mode: str | None = None,
) -> list[RetrievedChunk]:
    """Cari potongan dokumen yang paling relevan (PRD §9 dan §25).

    Args:
        mode: `hybrid`, `vector`, atau `fulltext`. Bawaannya mengikuti
            `RAG_HYBRID_ENABLED`. Berguna untuk membandingkan ketiganya
            saat menelusuri jawaban yang meleset.
    """
    limit = top_k or settings.rag_top_k
    mode = mode or ("hybrid" if settings.rag_hybrid_enabled else "vector")

    if mode == "vector":
        return await search_vector(db, query, limit)
    if mode == "fulltext":
        return search_fulltext(db, query, limit)

    # Tiap jalur mengambil lebih banyak daripada yang diminta, supaya
    # penggabungan punya bahan untuk saling mengangkat.
    lebar = max(limit * 3, 10)
    vektor = await search_vector(db, query, lebar)
    teks = search_fulltext(db, query, lebar)
    return gabung_rrf(
        vektor,
        teks,
        bobot=(settings.rag_bobot_vektor, settings.rag_bobot_teks),
        limit=limit,
    )
