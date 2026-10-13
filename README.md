# VENOM4 Pro — Kali Linux Script Mode

Repository ini sekarang berfokus pada **script Python yang dijalankan lokal di Kali Linux**. Tidak ada web server, frontend browser, REST API, Docker, atau database remote.

## Fitur

- SQLite database lokal untuk:
  - authorization record;
  - scope rules;
  - asset inventory;
  - findings dan status lifecycle;
  - evidence checksum;
  - hasil scan;
  - audit events.
- Automatic **read-only** HTTP/HTTPS assessment.
- Scope enforcement sebelum scan.
- Rate limit, timeout, maximum response size, dan TLS verification.
- HTTP status dan redirect.
- Security headers.
- Cookie attributes.
- Passive technology disclosure.
- TLS handshake metadata.
- Pemeriksaan `robots.txt`, `sitemap.xml`, `openapi.json`, dan `swagger.json`.
- Export Markdown report.
- Semua data tersimpan lokal di `~/.local/share/venom4pro/venom4pro.db`.

## Batas keamanan

Mode script ini tidak menyediakan brute force, exploit execution, payload delivery, DDoS, ransomware, reverse shell, counter-attack, atau remote command execution. Scanner hanya memakai GET/HEAD terhadap target yang masuk active authorization scope.

File asli repo lama tetap ada di `legacy/original/` sebagai arsip dan tidak dipanggil oleh launcher aktif.

## Instalasi di Kali Linux

```bash
chmod +x install_venom4.sh run.sh venom4.py
./install_venom4.sh
```

Jika ingin menggunakan database berbeda:

```bash
VENOM4PRO_DB=/path/to/project.db ./run.sh status
```

## Alur penggunaan

### 1. Inisialisasi dan cek database

```bash
./run.sh init
./run.sh status
```

### 2. Buat authorization scope

Edit contoh JSON atau pakai langsung untuk local lab:

```bash
./run.sh authorization scripts/example_authorization.json
```

Setiap authorization baru menonaktifkan authorization aktif sebelumnya.

### 3. Tambahkan asset

```bash
./run.sh asset scripts/example_asset.json
```

Asset diberi flag `in_scope` berdasarkan authorization aktif.

### 4. Jalankan automatic read-only scan

```bash
./run.sh scan http://127.0.0.1:3000 --delay 1 --timeout 8
```

Target di luar scope akan ditolak. Hasil disimpan sebagai scan result dan evidence di SQLite.

Pilihan aman:

```bash
./run.sh scan https://authorized.example \
  --delay 1 \
  --timeout 10 \
  --max-body 512000 \
  --no-openapi
```

### 5. Kelola finding

```bash
./run.sh finding scripts/example_finding.json
./run.sh transition FINDING_ID open
./run.sh transition FINDING_ID accepted
```

### 6. Audit dan laporan

```bash
./run.sh audit
./run.sh report ./reports/assessment.md
```

## Struktur penting

```text
venom4.py                         # entry point CLI
run.sh                            # launcher virtualenv
scripts/venom4pro.py              # parser dan workflow CLI
bgxdesk/services/sqlite_store.py  # SQLite repositories
bgxdesk/services/scanner.py       # scanner read-only reusable
bgxdesk/domain/models.py           # domain models
scripts/example_*.json             # contoh input
legacy/original/                   # file lama yang dipertahankan
```

## Testing

```bash
python3 -m compileall -q venom4.py scripts bgxdesk tests
pytest -q
```

## Catatan kualitas kode

Permintaan minimal 3.000 baris **per file** tidak diterapkan sebagai duplikasi atau padding. Arsitektur dipecah berdasarkan tanggung jawab agar dapat dirawat dan diaudit. Target yang lebih sehat adalah menambah logika nyata, test, migration, dan dokumentasi secara modular—bukan membuat satu file ribuan baris yang sulit diverifikasi.
