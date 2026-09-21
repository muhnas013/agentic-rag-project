-- Data sample untuk SQL Tool (PRD Fase 5).
--
-- Temanya sengaja disambungkan dengan dokumen contoh yang sudah diindeks
-- (kebijakan retensi, panduan cuti, SOP pengadaan), sehingga Agent bisa
-- diuji pada pertanyaan yang menuntut dua tool sekaligus: aturan cutinya
-- dari dokumen lewat RAG_Search, realisasinya dari tabel lewat SQL_Query.
--
-- Berkas ini dijalankan otomatis saat volume database masih kosong. Untuk
-- database yang sudah berisi:
--   docker exec -i agentic-rag-db psql -U postgres -d agentic_rag \
--     < docker/postgres/init/03-sample-data.sql
-- Aman diulang: isinya ditulis ulang, bukan ditumpuk.

CREATE TABLE IF NOT EXISTS pegawai (
    id            BIGSERIAL PRIMARY KEY,
    nama          VARCHAR(100) NOT NULL,
    nip           VARCHAR(30)  NOT NULL UNIQUE,
    bagian        VARCHAR(50)  NOT NULL,
    jabatan       VARCHAR(80)  NOT NULL,
    tanggal_masuk DATE         NOT NULL
);

CREATE TABLE IF NOT EXISTS pengajuan_cuti (
    id              BIGSERIAL PRIMARY KEY,
    pegawai_id      BIGINT      NOT NULL REFERENCES pegawai(id),
    jenis           VARCHAR(30) NOT NULL,   -- tahunan, sakit, besar, melahirkan
    tanggal_mulai   DATE        NOT NULL,
    tanggal_selesai DATE        NOT NULL,
    jumlah_hari     INT         NOT NULL,
    status          VARCHAR(20) NOT NULL,   -- diajukan, disetujui, ditolak
    dibuat_pada     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pengajuan_cuti_pegawai ON pengajuan_cuti(pegawai_id);
CREATE INDEX IF NOT EXISTS ix_pengajuan_cuti_status  ON pengajuan_cuti(status);

-- Urutan penghapusan mengikuti foreign key.
TRUNCATE pengajuan_cuti, pegawai RESTART IDENTITY CASCADE;

INSERT INTO pegawai (nama, nip, bagian, jabatan, tanggal_masuk) VALUES
    ('Andi Pratama',      '198501012010011001', 'Kepegawaian', 'Kepala Bagian',        '2010-01-01'),
    ('Siti Rahmawati',    '198803152012022002', 'Kepegawaian', 'Analis Kepegawaian',   '2012-02-15'),
    ('Budi Santoso',      '199002202015031003', 'Keuangan',    'Bendahara',            '2015-03-20'),
    ('Dewi Lestari',      '199105102016042004', 'Keuangan',    'Staf Akuntansi',       '2016-04-10'),
    ('Rudi Hartono',      '198707252011011005', 'Umum',        'Kepala Bagian Umum',   '2011-01-25'),
    ('Maya Sari',         '199310182018032006', 'Umum',        'Staf Arsip',           '2018-03-18'),
    ('Joko Widodo',       '198912052014011007', 'Pengadaan',   'Pejabat Pembuat Komitmen', '2014-01-05'),
    ('Rina Melati',       '199407222019042008', 'Pengadaan',   'Staf Pengadaan',       '2019-04-22'),
    ('Agus Setiawan',     '199601302020031009', 'TIK',         'Pranata Komputer',     '2020-03-30'),
    ('Nurul Hidayah',     '199709142021042010', 'TIK',         'Staf Jaringan',        '2021-04-14'),
    ('Bambang Sugeng',    '198403082009011011', 'Kepegawaian', 'Analis SDM',           '2009-01-08'),
    ('Fitri Handayani',   '199802252022042012', 'Keuangan',    'Staf Verifikasi',      '2022-04-25');

INSERT INTO pengajuan_cuti (pegawai_id, jenis, tanggal_mulai, tanggal_selesai, jumlah_hari, status) VALUES
    ( 1, 'tahunan',    '2026-01-12', '2026-01-16',  5, 'disetujui'),
    ( 1, 'tahunan',    '2026-06-08', '2026-06-12',  5, 'disetujui'),
    ( 2, 'tahunan',    '2026-02-03', '2026-02-05',  3, 'disetujui'),
    ( 2, 'sakit',      '2026-04-20', '2026-04-22',  3, 'disetujui'),
    ( 2, 'tahunan',    '2026-09-28', '2026-09-30',  3, 'diajukan'),
    ( 3, 'tahunan',    '2026-03-16', '2026-03-20',  5, 'disetujui'),
    ( 3, 'sakit',      '2026-07-06', '2026-07-07',  2, 'disetujui'),
    ( 4, 'melahirkan', '2026-05-04', '2026-07-31', 90, 'disetujui'),
    ( 5, 'tahunan',    '2026-01-26', '2026-01-30',  5, 'disetujui'),
    ( 5, 'besar',      '2026-08-03', '2026-08-28', 26, 'disetujui'),
    ( 6, 'tahunan',    '2026-02-17', '2026-02-19',  3, 'ditolak'),
    ( 6, 'tahunan',    '2026-05-11', '2026-05-15',  5, 'disetujui'),
    ( 7, 'tahunan',    '2026-04-06', '2026-04-10',  5, 'disetujui'),
    ( 7, 'sakit',      '2026-09-15', '2026-09-16',  2, 'disetujui'),
    ( 8, 'tahunan',    '2026-06-22', '2026-06-26',  5, 'disetujui'),
    ( 8, 'tahunan',    '2026-09-21', '2026-09-25',  5, 'diajukan'),
    ( 9, 'tahunan',    '2026-03-02', '2026-03-04',  3, 'disetujui'),
    ( 9, 'tahunan',    '2026-07-13', '2026-07-17',  5, 'disetujui'),
    (10, 'sakit',      '2026-08-10', '2026-08-12',  3, 'disetujui'),
    (10, 'tahunan',    '2026-09-21', '2026-09-22',  2, 'diajukan'),
    (11, 'besar',      '2026-02-02', '2026-02-27', 26, 'disetujui'),
    (11, 'tahunan',    '2026-08-17', '2026-08-21',  5, 'disetujui'),
    (12, 'tahunan',    '2026-05-25', '2026-05-27',  3, 'ditolak'),
    (12, 'sakit',      '2026-09-01', '2026-09-02',  2, 'disetujui');

-- Tabel dibuat sesudah user read-only ada, sehingga hak bacanya datang dari
-- ALTER DEFAULT PRIVILEGES pada skrip 02. Grant eksplisit di bawah membuat
-- berkas ini tetap benar walau dijalankan manual di database lama.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rag_readonly') THEN
        GRANT SELECT ON pegawai, pengajuan_cuti TO rag_readonly;
    END IF;
END
$$;
