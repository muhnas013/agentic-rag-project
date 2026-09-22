"""Uji autentikasi dan otorisasi (PRD §18 dan §24)."""

import pytest

from backend.auth import Peran, hash_sandi, sandi_cocok
from backend.config import settings


class TestKataSandi:
    def test_hash_tidak_memuat_teks_aslinya(self):
        h = hash_sandi("rahasia123")
        assert "rahasia123" not in h
        assert h.startswith("$2")

    def test_sandi_benar_cocok(self):
        assert sandi_cocok("rahasia123", hash_sandi("rahasia123"))

    def test_sandi_salah_tidak_cocok(self):
        assert not sandi_cocok("salah", hash_sandi("rahasia123"))

    def test_hash_sama_dua_kali_tetap_berbeda(self):
        """Salt acak: dua hash dari sandi sama tidak boleh identik."""
        assert hash_sandi("sama") != hash_sandi("sama")

    def test_hash_rusak_ditolak_tanpa_galat(self):
        """Hash rusak tidak boleh membedakan akun ada dan tidak ada."""
        assert not sandi_cocok("apa pun", "bukan-hash-bcrypt")


class TestLogin:
    def test_kredensial_benar_memberi_token(self, client_anonim):
        r = client_anonim.post(
            "/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        assert r.status_code == 200

        data = r.json()
        assert data["token_type"] == "bearer"
        assert data["role"] == Peran.ADMIN
        assert data["expires_in"] == settings.jwt_expire_minutes * 60

    def test_sandi_salah_ditolak(self, client_anonim):
        r = client_anonim.post(
            "/auth/login",
            json={"username": settings.admin_username, "password": "salah"},
        )
        assert r.status_code == 401

    def test_pesan_sama_untuk_akun_ada_dan_tidak_ada(self, client_anonim):
        """Pesan yang berbeda bisa dipakai menebak akun mana yang terdaftar."""
        a = client_anonim.post(
            "/auth/login", json={"username": settings.admin_username, "password": "salah"}
        )
        b = client_anonim.post(
            "/auth/login", json={"username": "tidak-ada-sama-sekali", "password": "salah"}
        )
        assert a.status_code == b.status_code == 401
        assert a.json()["detail"] == b.json()["detail"]


class TestTanpaToken:
    @pytest.mark.parametrize(
        "metode,path,body",
        [
            ("get", "/documents", None),
            ("get", "/auth/me", None),
            ("post", "/query", {"query": "apa saja"}),
            ("post", "/chat", {"session_id": "x", "message": "halo"}),
            ("get", "/chat/history?session_id=x", None),
        ],
    )
    def test_ditolak_401(self, client_anonim, metode, path, body):
        r = getattr(client_anonim, metode)(path, **({"json": body} if body else {}))
        assert r.status_code == 401

    def test_health_tetap_terbuka(self, client_anonim):
        """Frontend memakainya sebelum pengguna sempat masuk."""
        assert client_anonim.get("/health").status_code == 200

    def test_token_asal_ditolak(self, client_anonim):
        r = client_anonim.get("/auth/me", headers={"Authorization": "Bearer bukan.token.asli"})
        assert r.status_code == 401


class TestPemisahanPeran:
    """PRD §18 menuntut ADMIN, USER, dan READ_ONLY dipisahkan."""

    def test_read_only_boleh_membaca(self, buat_pengguna):
        c = buat_pengguna("uji_pembaca", "READ_ONLY")
        assert c.get("/documents").status_code == 200

    def test_read_only_tidak_boleh_menambah_dokumen(self, buat_pengguna):
        c = buat_pengguna("uji_pembaca2", "READ_ONLY")
        r = c.post("/documents", json={"filename": "x.txt", "content": "isi"})
        assert r.status_code == 403
        assert "READ_ONLY" in r.json()["detail"]

    def test_user_boleh_menambah_dokumen(self, buat_pengguna, embedding_tiruan):
        c = buat_pengguna("uji_penulis", "USER")
        r = c.post("/documents", json={"filename": "uji-peran.txt", "content": "isi uji"})
        assert r.status_code == 200

    def test_user_tidak_boleh_mengelola_akun(self, buat_pengguna):
        c = buat_pengguna("uji_penulis2", "USER")
        assert c.get("/auth/users").status_code == 403

    def test_admin_boleh_semuanya(self, client):
        assert client.get("/auth/users").status_code == 200
        assert client.get("/documents").status_code == 200

    def test_peran_lebih_tinggi_mencakup_yang_lebih_rendah(self, client):
        """ADMIN lolos di tempat yang hanya menuntut USER."""
        r = client.post("/documents", json={"filename": "uji-admin.txt", "content": "isi"})
        assert r.status_code == 200


class TestAkunBaru:
    def test_nama_ganda_ditolak(self, client):
        client.post("/auth/users", json={"username": "uji_ganda", "password": "rahasia123"})
        r = client.post("/auth/users", json={"username": "uji_ganda", "password": "rahasia123"})
        assert r.status_code == 409

    def test_sandi_terlalu_pendek_ditolak(self, client):
        r = client.post("/auth/users", json={"username": "uji_pendek", "password": "123"})
        assert r.status_code == 422

    def test_nama_dengan_karakter_aneh_ditolak(self, client):
        r = client.post("/auth/users", json={"username": "a b/c", "password": "rahasia123"})
        assert r.status_code == 422
