"""Autentikasi dan otorisasi (PRD §18 dan §24).

PRD §18 menetapkan JWT untuk autentikasi dan pemisahan permission menjadi
ADMIN, USER, dan READ_ONLY. Berkas ini memuat ketiganya: penyimpanan kata
sandi, pembuatan token, dan dependency FastAPI yang menegakkan peran.

Pembagian peran mengikuti apa yang bisa diubah pengguna, bukan sekadar
tingkatan jabatan:

- READ_ONLY  hanya membaca — bertanya, mencari, melihat riwayat
- USER       ditambah menambah dokumen dan mengunggah berkas
- ADMIN      ditambah mengelola pengguna
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from enum import Enum

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import User

logger = logging.getLogger(__name__)

# auto_error=False supaya ketiadaan header bisa ditangani sendiri —
# pesannya lebih jelas daripada galat bawaan FastAPI.
skema_token = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class Peran(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    READ_ONLY = "READ_ONLY"


# Peran yang lebih tinggi mencakup wewenang peran di bawahnya.
URUTAN: dict[str, int] = {Peran.READ_ONLY: 0, Peran.USER: 1, Peran.ADMIN: 2}


def hash_sandi(sandi: str) -> str:
    """Simpan kata sandi sebagai hash bcrypt, tidak pernah sebagai teks asli."""
    return bcrypt.hashpw(sandi.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def sandi_cocok(sandi: str, hash_tersimpan: str) -> bool:
    try:
        return bcrypt.checkpw(sandi.encode("utf-8"), hash_tersimpan.encode("utf-8"))
    except ValueError:
        # Hash yang rusak diperlakukan sebagai tidak cocok, bukan galat —
        # supaya tidak bisa dipakai membedakan akun yang ada dan tidak ada.
        return False


def buat_token(pengguna: User) -> tuple[str, int]:
    """Terbitkan token JWT. Mengembalikan (token, detik sampai kedaluwarsa)."""
    berlaku = timedelta(minutes=settings.jwt_expire_minutes)
    kedaluwarsa = datetime.now(UTC) + berlaku

    token = jwt.encode(
        {
            "sub": pengguna.username,
            "role": pengguna.role,
            "exp": kedaluwarsa,
            "iat": datetime.now(UTC),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, int(berlaku.total_seconds())


def baca_token(token: str) -> dict:
    """Verifikasi tanda tangan dan masa berlaku token.

    Raises:
        HTTPException 401: token tidak sah atau sudah kedaluwarsa.
    """
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sesi sudah berakhir. Silakan masuk kembali.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token tidak sah.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def pengguna_saat_ini(
    token: str | None = Depends(skema_token),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: pengguna yang sedang masuk.

    Bila `AUTH_ENABLED=false`, seluruh permintaan dianggap datang dari admin
    bawaan. Itu memudahkan pengembangan lokal, dan disengaja dapat dimatikan
    karena sistem ini memang ditujukan untuk berjalan di mesin sendiri.
    """
    if not settings.auth_enabled:
        pengguna = db.query(User).filter(User.username == settings.admin_username).first()
        if pengguna:
            return pengguna
        # Tanpa baris di database pun sistem tetap bisa dipakai saat auth mati.
        return User(username=settings.admin_username, role=Peran.ADMIN, password_hash="")

    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Permintaan ini membutuhkan autentikasi.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    data = baca_token(token)
    pengguna = db.query(User).filter(User.username == data.get("sub")).first()
    if not pengguna or not pengguna.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Akun tidak ditemukan atau dinonaktifkan."
        )
    return pengguna


def wajib_peran(minimal: Peran):
    """Bangun dependency yang menuntut peran minimal tertentu.

    Peran dibandingkan berdasarkan tingkat, bukan kesamaan persis, sehingga
    ADMIN otomatis lolos di tempat yang menuntut USER.
    """

    def pemeriksa(pengguna: User = Depends(pengguna_saat_ini)) -> User:
        if URUTAN.get(pengguna.role, -1) < URUTAN[minimal]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Peran '{pengguna.role}' tidak berwenang. "
                f"Dibutuhkan minimal '{minimal.value}'.",
            )
        return pengguna

    return pemeriksa


def siapkan_akun_bawaan(db: Session) -> None:
    """Buat akun admin bawaan bila database masih kosong.

    Tanpa ini, sistem yang baru dipasang tidak punya satu pun cara untuk
    masuk. Kata sandinya diambil dari `.env` dan wajib diganti sebelum
    dipakai di luar mesin sendiri.
    """
    if db.query(User).count() > 0:
        return

    db.add(
        User(
            username=settings.admin_username,
            password_hash=hash_sandi(settings.admin_password),
            role=Peran.ADMIN,
        )
    )
    db.commit()
    logger.warning(
        "Akun admin bawaan '%s' dibuat. Ganti ADMIN_PASSWORD di .env "
        "sebelum dipakai di luar mesin sendiri.",
        settings.admin_username,
    )
