# VENOM4 Pro / BGXTEAM Security Desk

**VENOM4 Pro** kini menjadi desktop security-assessment workspace modern berbasis PySide6. Repository ini menggabungkan identitas dan entry point `venom4.py` dengan modul BGXTEAM Security Desk yang modular, offline-first, dan audit-friendly.

## Multi-GUI modern

Aplikasi memiliki beberapa panel navigasi:

- **Overview** — metrik aset, findings, evidence, risk score, dan activity feed.
- **Inventory** — deteksi executable lokal, policy label, versi, dan kategori.
- **Authorization** — client, engagement, reviewer, scope, approved methods, dan asset list.
- **Findings** — severity, CVSS, status lifecycle, impact, remediation, dan asset.
- **Reports & Audit** — export Markdown, CSV, JSON, serta event trail.

### Visual identity

GUI menggunakan wallpaper 3D bertema **Venom / Cyber Security / Bug Hunter**:

```text
assets/wallpapers/venom4pro-main.png     # desktop GUI 16:9
assets/wallpapers/venom4pro-wide.png     # terminal/CLI 21:9
assets/wallpapers/venom4pro-compact.png  # panel compact 4:3
```

Wallpaper utama otomatis dimuat oleh `bgxdesk.main` sebagai background dengan
overlay gelap agar tabel, log, dan form tetap terbaca. Varian wide dan compact
tersedia untuk panel atau launcher tambahan.

## Automatic assessment yang aman

CLI scanner melakukan pemeriksaan **read-only** terhadap URL yang lolos authorization scope:

- HTTP status dan redirect.
- Security headers.
- Cookie attributes.
- TLS handshake dan certificate metadata.
- Technology disclosure pasif.
- `robots.txt`, `sitemap.xml`, dan endpoint dokumentasi OpenAPI umum.
- Rate limit, timeout, maximum response size, dan stop signal.
- Evidence otomatis dan audit event.

Perintah:

```bash
./install_venom4.sh
.venv/bin/python venom4.py
.venv/bin/python -m bgxdesk.cli status
.venv/bin/python -m bgxdesk.cli inventory
.venv/bin/python -m bgxdesk.cli scan https://authorized.example report.md --delay 1
```

Sebelum scan, buat authorization record dari GUI. Target tanpa active authorization atau target di luar scope akan ditolak.

## Instalasi

```bash
chmod +x install_venom4.sh venom4.py
./install_venom4.sh
```

Data project disimpan secara lokal pada `~/.local/share/bgxteam-security-desk/project.json` dengan backup atomik `.bak`. Tidak ada web server, database remote, atau remote command execution.

## Security boundary

Kode lama repo ini mendeskripsikan brute force, DDoS, ransomware, reverse shell, counter-attack, destructive firewall changes, dan command concatenation. Implementasi tersebut **tidak diintegrasikan**. Entry point `venom4.py` sekarang hanya membuka GUI Security Desk yang baru.

Fitur yang sengaja tidak tersedia:

- brute-force credential guessing;
- exploit execution atau payload delivery;
- DDoS/flooding;
- ransomware atau perubahan file target;
- reverse shell;
- counter-attack;
- remote command execution;
- scanner yang bypass authorization scope.

Untuk lab milik sendiri, gunakan aplikasi latihan lokal seperti OWASP Juice Shop dengan network isolation dan snapshot VM. Assessment pada sistem nyata harus memiliki authorization tertulis, scope eksplisit, time window, rate limit, dan emergency contact.

## Struktur

```text
venom4.py                 # safe launcher
bgxdesk/main.py           # multi-panel PySide6 GUI
bgxdesk/cli.py            # offline CLI
bgxdesk/domain/models.py  # domain models and validation
bgxdesk/services/storage.py
bgxdesk/services/assessment.py
bgxdesk/services/scanner.py
 tests/test_core.py
```

## Testing

```bash
.venv/bin/python -m compileall -q bgxdesk tests
.venv/bin/pytest -q
```
