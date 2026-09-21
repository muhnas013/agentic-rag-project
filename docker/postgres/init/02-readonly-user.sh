#!/bin/bash
# Membuat user read-only khusus SQL Agent (PRD §18 - Database Security,
# keputusan D-05). Pembatasan ditegakkan pada level grant PostgreSQL,
# bukan sekadar validasi di kode aplikasi.
set -euo pipefail

: "${SQL_AGENT_DB_USER:?SQL_AGENT_DB_USER wajib diisi}"
: "${SQL_AGENT_DB_PASSWORD:?SQL_AGENT_DB_PASSWORD wajib diisi}"

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" \
     -v agent_user="$SQL_AGENT_DB_USER" \
     -v agent_password="$SQL_AGENT_DB_PASSWORD" \
     -v db_name="$POSTGRES_DB" \
     -v owner="$POSTGRES_USER" <<-'SQL'
	-- Role tanpa hak membuat apa pun.
	CREATE ROLE :"agent_user" LOGIN PASSWORD :'agent_password'
	    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;

	-- Cegah role ini (dan PUBLIC) membuat objek baru di schema public.
	REVOKE CREATE ON SCHEMA public FROM PUBLIC;
	REVOKE ALL ON DATABASE :"db_name" FROM PUBLIC;

	GRANT CONNECT ON DATABASE :"db_name" TO :"agent_user";
	GRANT USAGE ON SCHEMA public TO :"agent_user";

	-- Tabel dibuat belakangan oleh SQLAlchemy, jadi hak baca diberikan
	-- lewat default privileges agar otomatis berlaku pada tabel baru.
	-- Hanya SELECT: tidak ada INSERT/UPDATE/DELETE/DROP.
	GRANT SELECT ON ALL TABLES IN SCHEMA public TO :"agent_user";
	ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public
	    GRANT SELECT ON TABLES TO :"agent_user";

	-- Query timeout ditegakkan di level role (PRD §18).
	ALTER ROLE :"agent_user" SET statement_timeout = '10s';
	ALTER ROLE :"agent_user" SET default_transaction_read_only = on;
SQL

echo "User read-only '$SQL_AGENT_DB_USER' dibuat."
