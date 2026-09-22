"""Titik masuk FastAPI (PRD §20).

Endpoint pada fase ini:

    POST /auth/login      tukar kredensial dengan token JWT
    GET  /auth/me         identitas dan peran pemilik token
    POST /auth/users      tambah akun (ADMIN)
    GET  /auth/users      daftar akun (ADMIN)
    GET  /health          status aplikasi, database, dan provider model
    POST /upload          unggah berkas lalu olah menjadi embedding
    POST /documents       tambah dokumen dari teks langsung
    GET  /documents       daftar berkas yang sudah diunggah
    GET  /models          daftar model percakapan yang tersedia di Ollama
    POST /query           pencarian RAG mentah, tanpa LLM
    POST /chat            jawaban berbasis dokumen
    GET  /chat/history    riwayat percakapan satu sesi
    GET  /chat/sessions   daftar percakapan untuk sidebar
    DELETE /chat/sessions/{id}  hapus satu percakapan

`POST /chat` dilayani Agent Orchestrator (`agent.py`), yang memilih sendiri
tool yang cocok. `POST /query` melewati Agent maupun LLM, sehingga berguna
untuk memeriksa mutu pencarian secara terpisah.
"""

from __future__ import annotations

import io
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.agent import run_agent
from backend.auth import (
    Peran,
    buat_token,
    hash_sandi,
    pengguna_saat_ini,
    sandi_cocok,
    siapkan_akun_bawaan,
    wajib_peran,
)
from backend.config import settings
from backend.database import (
    SessionLocal,
    check_database_connection,
    engine,
    get_db,
    init_database,
)
from backend.models import ChatHistory, Document, User
from backend.schemas import (
    ChatHistoryResponse,
    ChatMessageItem,
    ChatRequest,
    ChatResponse,
    ChatSessionSummary,
    DocumentSummary,
    HealthResponse,
    LoginRequest,
    ModelListResponse,
    QueryRequest,
    QueryResponse,
    SourceItem,
    TextDocumentRequest,
    TokenResponse,
    UploadResponse,
    UserCreate,
    UserOut,
)
from backend.services import document_service
from backend.services.document_service import (
    DocumentProcessingError,
    RetrievedChunk,
    UploadValidationError,
)
from backend.services.embedding_service import EmbeddingError
from backend.services.llm_service import LLMError, daftar_model_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Cukup untuk memeriksa signature dan MIME tanpa memuat seluruh berkas.
HEAD_SIZE = 8192

# Banyaknya pesan lampau yang ikut dikirim sebagai konteks percakapan.
HISTORY_LIMIT = 8


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Siapkan extension pgvector dan tabel saat aplikasi start."""
    try:
        init_database()
        logger.info("Database siap. Tabel chat_history, documents, dan users tersedia.")

        db = SessionLocal()
        try:
            siapkan_akun_bawaan(db)
        finally:
            db.close()

        if not settings.auth_enabled:
            logger.warning(
                "AUTH_ENABLED=false — seluruh endpoint terbuka tanpa autentikasi. "
                "Hanya untuk pengembangan di mesin sendiri."
            )
    except Exception as exc:  # pragma: no cover - bergantung lingkungan
        # Aplikasi tetap dinyalakan agar /health bisa melaporkan penyebabnya.
        logger.error("Inisialisasi database gagal: %s", exc)

    logger.info(
        "Provider LLM=%s (%s), embedding=%s (%s, %d dimensi)",
        settings.llm_provider.value,
        settings.llm_model_name or "-",
        settings.embedding_provider.value,
        settings.embedding_model_name,
        settings.embedding_dim,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    description="Agentic RAG — Local AI System",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_source(chunk: RetrievedChunk, excerpt_length: int = 300) -> SourceItem:
    excerpt = chunk.content[:excerpt_length]
    if len(chunk.content) > excerpt_length:
        excerpt += "…"
    return SourceItem(
        filename=chunk.filename,
        score=chunk.score,
        chunk_index=chunk.metadata.get("chunk_index"),
        excerpt=excerpt,
    )


# Judul di sidebar dipotong supaya satu baris tetap terbaca utuh.
PANJANG_JUDUL = 60


def _potong_judul(pesan: str) -> str:
    bersih = " ".join(pesan.split())
    if len(bersih) <= PANJANG_JUDUL:
        return bersih or "(tanpa judul)"
    return bersih[:PANJANG_JUDUL].rstrip() + "…"


def _recent_history(db: Session, session_id: str) -> list[dict[str, str]]:
    """Ambil beberapa pesan terakhir sebagai konteks percakapan.

    Jumlahnya dibatasi karena jendela konteks model hanya 8K token
    (keputusan D-02); riwayat panjang akan menggusur hasil tool.
    """
    rows = db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.id.desc())
        .limit(HISTORY_LIMIT)
    ).scalars().all()

    return [{"role": row.role, "content": row.message} for row in reversed(rows)]


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Status sistem (PRD §20).

    Sengaja tidak menuntut autentikasi: frontend memakainya untuk menampilkan
    status sebelum pengguna sempat masuk, dan isinya tidak memuat data
    siapa pun.

    Ketersediaan provider model sengaja tidak ikut diperiksa agar endpoint ini
    tetap cepat dan tidak memakai kuota API pada setiap pemanggilan.
    """
    database_ok = check_database_connection()

    vector_ok = False
    if database_ok:
        try:
            with engine.connect() as conn:
                vector_ok = bool(
                    conn.execute(
                        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                    ).scalar()
                )
        except Exception as exc:
            logger.warning("Pemeriksaan extension vector gagal: %s", exc)

    return HealthResponse(
        status="ok" if (database_ok and vector_ok) else "degraded",
        app=settings.app_name,
        environment=settings.app_env,
        database=database_ok,
        vector_extension=vector_ok,
        llm_provider=settings.llm_provider.value,
        llm_model=settings.llm_model_name or "-",
        embedding_provider=settings.embedding_provider.value,
        embedding_model=settings.embedding_model_name,
        embedding_dim=settings.embedding_dim,
    )


# --------------------------------------------------------------------------
# Autentikasi (PRD §18)
# --------------------------------------------------------------------------


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Tukar nama pengguna dan kata sandi dengan token JWT."""
    pengguna = db.query(User).filter(User.username == payload.username).first()

    # Pesan galatnya sengaja sama untuk nama yang salah maupun sandi yang
    # salah, supaya tidak bisa dipakai menebak akun mana yang ada.
    if not pengguna or not sandi_cocok(payload.password, pengguna.password_hash):
        logger.warning("Percobaan masuk gagal untuk %r", payload.username)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Nama pengguna atau kata sandi salah."
        )

    if not pengguna.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Akun dinonaktifkan.")

    token, berlaku = buat_token(pengguna)
    return TokenResponse(
        access_token=token,
        expires_in=berlaku,
        username=pengguna.username,
        role=pengguna.role,
    )


@app.get("/auth/me", response_model=UserOut, tags=["auth"])
def akun_saya(pengguna: User = Depends(pengguna_saat_ini)) -> UserOut:
    """Identitas dan peran pemilik token yang sedang dipakai."""
    return UserOut.model_validate(pengguna, from_attributes=True)


@app.post("/auth/users", response_model=UserOut, tags=["auth"])
def tambah_pengguna(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.ADMIN)),
) -> UserOut:
    """Tambah akun baru. Hanya ADMIN."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Pengguna '{payload.username}' sudah ada."
        )

    pengguna = User(
        username=payload.username,
        password_hash=hash_sandi(payload.password),
        role=payload.role,
    )
    db.add(pengguna)
    db.commit()
    db.refresh(pengguna)
    logger.info("Pengguna baru '%s' dibuat dengan peran %s", pengguna.username, pengguna.role)
    return UserOut.model_validate(pengguna, from_attributes=True)


@app.get("/auth/users", response_model=list[UserOut], tags=["auth"])
def daftar_pengguna(
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.ADMIN)),
) -> list[UserOut]:
    """Daftar seluruh akun. Hanya ADMIN."""
    return [
        UserOut.model_validate(u, from_attributes=True)
        for u in db.query(User).order_by(User.id).all()
    ]


# --------------------------------------------------------------------------
# Dokumen
# --------------------------------------------------------------------------


@app.post("/upload", response_model=UploadResponse, tags=["documents"])
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.USER)),
) -> UploadResponse:
    """Unggah dokumen lalu ubah menjadi embedding (PRD §20).

    Gambar disimpan tanpa diolah: ekstraksi teksnya menunggu OCR Tool di Fase 5.
    """
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nama berkas kosong.")

    head = await file.read(HEAD_SIZE)
    await file.seek(0)

    # Isi berkas diperiksa lebih dulu agar unggahan yang ditolak tidak
    # pernah menyentuh disk.
    try:
        extension = document_service.validate_upload(file.filename, head)
    except UploadValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    try:
        stored_path, _size = document_service.save_upload(file.file, file.filename)
    except UploadValidationError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc

    if extension in settings.allowed_image_extensions:
        return UploadResponse(
            filename=file.filename,
            status="stored",
            detail="Gambar disimpan. Ekstraksi teks menunggu OCR Tool (Fase 5).",
        )

    try:
        chunks = await document_service.ingest_document(
            db,
            original_filename=file.filename,
            stored_path=stored_path,
            extension=extension,
        )
    except (DocumentProcessingError, EmbeddingError) as exc:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return UploadResponse(filename=file.filename, status="processed", chunks=chunks)


@app.post("/documents", response_model=UploadResponse, tags=["documents"])
async def add_text_document(
    payload: TextDocumentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.USER)),
) -> UploadResponse:
    """Tambah dokumen dari teks langsung.

    Memudahkan pengujian pipeline RAG tanpa menyiapkan berkas.
    """
    try:
        buffer = io.BytesIO(payload.content.encode("utf-8"))
        stored_path, _ = document_service.save_upload(buffer, "inline.txt")
        chunks = await document_service.ingest_document(
            db,
            original_filename=payload.filename,
            stored_path=stored_path,
            extension=".txt",
        )
    except (DocumentProcessingError, EmbeddingError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return UploadResponse(filename=payload.filename, status="processed", chunks=chunks)


def _gambar_terunggah() -> list[DocumentSummary]:
    """Gambar yang tersimpan di folder unggahan.

    Berkas disimpan sebagai `<uuid>__<nama-asli>` (keputusan D-12); yang
    ditampilkan adalah bagian setelah `__`, karena nama itulah yang diketik
    pengguna dan yang dikenali `Image_OCR`. Berkas lama dari sebelum D-12
    tidak punya bagian itu, jadi namanya dipakai apa adanya.

    Satu nama yang diunggah berkali-kali muncul sekali saja, memakai waktu
    unggahan terbarunya — sama seperti dokumen yang dikelompokkan per nama.
    """
    dasar = Path(settings.upload_dir)
    if not dasar.is_dir():
        return []

    terbaru: dict[str, float] = {}
    for berkas in dasar.iterdir():
        if not berkas.is_file():
            continue
        if berkas.suffix.lower() not in settings.allowed_image_extensions:
            continue
        nama = berkas.name.split("__", 1)[1] if "__" in berkas.name else berkas.name
        waktu = berkas.stat().st_mtime
        if waktu > terbaru.get(nama, 0.0):
            terbaru[nama] = waktu

    return [
        DocumentSummary(
            filename=nama,
            chunks=0,
            created_at=datetime.fromtimestamp(waktu),
            jenis="gambar",
        )
        for nama, waktu in terbaru.items()
    ]


@app.get("/documents", response_model=list[DocumentSummary], tags=["documents"])
def list_documents(
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.READ_ONLY)),
) -> list[DocumentSummary]:
    """Daftar berkas yang sudah diunggah, terbaru lebih dulu.

    Dua sumber digabung di sini karena di mata pengguna keduanya sama-sama
    "yang sudah saya unggah", walau nasibnya berbeda: dokumen teks menjadi
    potongan berembedding di tabel `documents`, sedangkan gambar hanya
    disimpan ke disk dan teksnya baru dibaca ketika `Image_OCR` dipanggil
    (lihat `POST /upload`). Menampilkan yang pertama saja membuat gambar
    yang baru diunggah tampak hilang — dan justru namanya yang dibutuhkan
    pengguna untuk menanyakan isinya.
    """
    rows = db.execute(
        select(
            Document.filename,
            func.count(Document.id).label("chunks"),
            func.min(Document.created_at).label("created_at"),
        )
        .group_by(Document.filename)
        .order_by(func.min(Document.created_at).desc())
    ).all()

    dokumen = [
        DocumentSummary(filename=filename, chunks=chunks, created_at=created_at)
        for filename, chunks, created_at in rows
    ]

    return sorted(
        dokumen + _gambar_terunggah(), key=lambda d: d.created_at, reverse=True
    )


@app.get("/models", response_model=ModelListResponse, tags=["system"])
async def list_models(
    _: User = Depends(wajib_peran(Peran.READ_ONLY)),
) -> ModelListResponse:
    """Model percakapan yang terpasang di Ollama (PRD §4.2).

    Daftarnya dibaca langsung dari Ollama tiap kali diminta, bukan disimpan
    di `.env`: model bisa ditambah atau dihapus dengan `ollama pull` dan
    `ollama rm` tanpa menyentuh aplikasi, dan daftar yang disalin akan
    menua tanpa ada yang menyadarinya.
    """
    try:
        tersedia = await daftar_model_llm()
    except LLMError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    # Model bawaan selalu ikut terdaftar walau belum diunduh, supaya
    # antarmuka tidak menampilkan pilihan aktif yang tidak ada di daftarnya.
    if settings.ollama_llm_model not in tersedia:
        tersedia = sorted([*tersedia, settings.ollama_llm_model])

    return ModelListResponse(models=tersedia, default=settings.ollama_llm_model)


# --------------------------------------------------------------------------
# RAG
# --------------------------------------------------------------------------


@app.post("/query", response_model=QueryResponse, tags=["rag"])
async def query_documents(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.READ_ONLY)),
) -> QueryResponse:
    """Pencarian kemiripan mentah, tanpa LLM.

    Memisahkan mutu retrieval dari mutu jawaban: bila /chat menjawab keliru,
    endpoint ini menunjukkan apakah penyebabnya ada di pencarian atau di model.
    """
    try:
        chunks = await document_service.search_similar_chunks(
            db, payload.query, payload.top_k, mode=payload.mode
        )
    except EmbeddingError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return QueryResponse(
        query=payload.query, results=[_to_source(chunk) for chunk in chunks]
    )


@app.post("/chat", response_model=ChatResponse, tags=["agent"])
async def chat_endpoint(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.READ_ONLY)),
) -> ChatResponse:
    """Jawaban dari Agent Orchestrator (PRD §14 dan §20).

    Agent memilih sendiri tool yang dipakai. Kolom `tool_used` pada respons
    menyebut tool mana yang benar-benar dipanggil, atau `none` bila
    pertanyaannya dijawab langsung.
    """
    riwayat = _recent_history(db, payload.session_id)

    # Nama model diperiksa terhadap daftar yang benar-benar ada di Ollama.
    # Pemeriksaan ini menambah satu panggilan HTTP lokal — hitungan
    # milidetik, tidak berarti dibanding waktu inferensi — dan imbalannya
    # galat yang jelas menyebut pilihan mana yang salah, bukan kegagalan
    # dari dalam Ollama yang sulit dilacak sampai ke penyebabnya.
    model = payload.model or None
    if model:
        try:
            tersedia = await daftar_model_llm()
        except LLMError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
        if model not in tersedia:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Model '{model}' tidak terpasang di Ollama. "
                f"Pilihan yang ada: {', '.join(tersedia) or '(kosong)'}.",
            )

    try:
        hasil = await run_agent(payload.message, history=riwayat, model=model)
    except LLMError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    db.add_all(
        [
            ChatHistory(session_id=payload.session_id, role="user", message=payload.message),
            ChatHistory(session_id=payload.session_id, role="assistant", message=hasil.answer),
        ]
    )
    db.commit()

    return ChatResponse(
        answer=hasil.answer,
        tool_used=hasil.tool_used,
        sources=[_to_source(chunk) for chunk in hasil.sources],
    )


@app.get("/chat/sessions", response_model=list[ChatSessionSummary], tags=["rag"])
def chat_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.READ_ONLY)),
) -> list[ChatSessionSummary]:
    """Daftar percakapan, terbaru lebih dulu.

    Judulnya diambil dari pesan pertama pengguna. Itu pilihan yang sengaja
    sederhana: meminta model membuatkan judul berarti satu panggilan LLM
    tambahan untuk tiap percakapan, dan pesan pertama hampir selalu sudah
    cukup mewakili isinya.
    """
    pertama = (
        select(
            ChatHistory.session_id,
            func.min(ChatHistory.id).label("id_pertama"),
            func.count(ChatHistory.id).label("jumlah"),
            func.min(ChatHistory.created_at).label("dimulai"),
            func.max(ChatHistory.created_at).label("terakhir"),
        )
        .group_by(ChatHistory.session_id)
        .subquery()
    )

    rows = db.execute(
        select(
            pertama.c.session_id,
            ChatHistory.message,
            pertama.c.jumlah,
            pertama.c.dimulai,
            pertama.c.terakhir,
        )
        .join(ChatHistory, ChatHistory.id == pertama.c.id_pertama)
        .order_by(pertama.c.terakhir.desc())
        .limit(limit)
    ).all()

    return [
        ChatSessionSummary(
            session_id=sid,
            judul=_potong_judul(pesan),
            jumlah_pesan=jumlah,
            dimulai=dimulai,
            terakhir=terakhir,
        )
        for sid, pesan, jumlah, dimulai, terakhir in rows
    ]


@app.delete("/chat/sessions/{session_id}", status_code=204, tags=["rag"])
def hapus_sesi(
    session_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.USER)),
) -> None:
    """Hapus satu percakapan beserta seluruh pesannya."""
    jumlah = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
    db.commit()
    if not jumlah:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Percakapan tidak ditemukan.")


@app.get("/chat/history", response_model=ChatHistoryResponse, tags=["rag"])
def chat_history(
    session_id: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(wajib_peran(Peran.READ_ONLY)),
) -> ChatHistoryResponse:
    """Riwayat percakapan satu sesi, diurutkan dari yang paling lama."""
    rows = db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.id.desc())
        .limit(limit)
    ).scalars().all()

    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            ChatMessageItem(
                id=row.id,
                session_id=row.session_id,
                role=row.role,
                message=row.message,
                created_at=row.created_at,
            )
            for row in reversed(rows)
        ],
    )
