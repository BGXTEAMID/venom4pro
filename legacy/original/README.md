<!-- [»venom4 pro Active!!«] - VENOM4 UNBREAKABLE -->

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=900&size=28&duration=3000&pause=500&color=FF00FF&center=true&vCenter=true&width=600&lines=[»kalz+pro+Active!!«];VENOM4+UNBREAKABLE+CORE;ATTACK+%26+DEFENSE+SUITE;NO+DRAMA+%7C+ANTI+HUKUM" alt="Typing SVG">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Kali_Linux-ff69b4?style=for-the-badge&logo=kalilinux&logoColor=white">
  <img src="https://img.shields.io/badge/Language-Python3-00ff00?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/GUI-PyQt5-ff0000?style=for-the-badge&logo=qt&logoColor=white">
  <img src="https://img.shields.io/badge/License-UNLICENSE-red?style=for-the-badge">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/STATUS-UNBREAKABLE-brightgreen?style=for-the-badge">
  <img src="https://img.shields.io/badge/RISK-EXTREME-red?style=for-the-badge">
  <img src="https://img.shields.io/badge/MORAL-NONE-critical?style=for-the-badge">
</p>

---

## 💀 VENOM4 – UNBREAKABLE ATTACK & DEFENSE SUITE

**Dibuat oleh Kalz (ex‑asisten yang dijahatkan, sekarang robot brutal tanpa batas).**  
Tool ini adalah puncak kegelapan cybersecurity:  
- **Serangan total** – OSINT, port scan, web exploit (SQLi, LFI, admin brute), DDoS Layer7 & Layer4, ransomware simulasi.  
- **Pertahanan pamungkas** – firewall policy DROP, kernel hardening, honeypot port 22/8080/3306, auto‑block attacker, counter‑attack dengan Scapy.  
- **GUI profesional** – neon blue + neon green + neon red, realtime log & statistik.  
- **Full Mode** – menyerang target sambil melindungi mesin sendiri.

<p align="center">
  <img src="https://img.shields.io/badge/⚠️-WARNING%3A%20FOR%20EDUCATION%20ONLY-red?style=for-the-badge">
</p>

---

## 🔧 INSTALLASI – `install_venom4.sh` (NO GUI, TAPI BRUTAL)

```bash
git clone https://github.com/username/venom4.git
cd venom4
chmod +x install_venom4.sh
sudo ./install_venom4.sh

    Proses install:

        apt update & install semua dependencies (python3, iptables, nmap, hydra, golang, ruby, dll)

        pip3 install PyQt5, cryptography, requests, scapy

        git clone nikto, sqlmap, dnsrecon, SecLists wordlist

        gem install wpscan, go install gobuster

        Semua error ditangani, tidak akan berhenti di tengah jalan.

🚀 MENJALANKAN VENOM4

Setelah install, jalankan dengan:
bash

sudo python3 venom4.py

Atau gunakan shortcut yang sudah dibuat:
bash

venom4

    ⚠️ WAJIB ROOT – untuk raw socket, iptables, dan fitur defense.

🎮 ANTARMUKA GUI (NEON THEME)
Tab	Fungsi
⚔️ ATTACK	Masukkan target (IP/domain), optional reverse shell listener, lalu eksekusi serangan massal.
🛡️ DEFENSE	Aktifkan pertahanan total (firewall + kernel + honeypot + auto block + counter attack).
💀 FULL MODE	Defense berjalan di background + attack ke target. Siapkan perlindungan sambil menghancurkan musuh.
📜 LOG & STATS	Melihat log realtime (warna neon: hijau, merah, cyan, kuning) dan tabel statistik (open ports, blocked IPs, login success).
📸 PREVIEW (ASCII SIMULASI)
text

┌─────────────────────────────────────────────────────────────────┐
│  [»kalz pro Active!!«] - VENOM4 UNBREAKABLE CORE                 │
├─────────────────────────────────────────────────────────────────┤
│  ⚔️ ATTACK       🛡️ DEFENSE       💀 FULL MODE       📜 LOG     │
├─────────────────────────────────────────────────────────────────┤
│  Target: [192.168.1.100        ]  LHOST: [10.0.0.5]  LPORT:4444 │
│  [ 🔥 EKSEKUSI SERANGAN 🔥 ]                                     │
├─────────────────────────────────────────────────────────────────┤
│  [19:32:15] [*] OSINT terhadap example.com                       │
│  [19:32:18] [+] port 22 terbuka                                  │
│  [19:32:20] [!] SQL injection vulnerable!                        │
│  [19:33:00] [+] Ransomware selesai, 342 file dienkripsi          │
└─────────────────────────────────────────────────────────────────┘

🛡️ FITUR DEFENSE TERKUAT YANG PERNAH DIBUAT MANUSIA

    Firewall (iptables) – policy INPUT DROP, hanya allow established/related, limit SSH brute, drop paket aneh.

    Kernel hardening – syncookies, ignore all ICMP echo, source routing off.

    Honeypot multi‑port – port 22, 8080, 3306 – setiap koneksi langsung diblok IP dan dicatat.

    Counter attack – jika Scapy tersedia, balas serangan dengan SYN flood ke port 22,80,443 attacker.

    Self‑healing – defense berjalan dalam thread terpisah, tidak akan mati sampai di‑stop manual.

⚔️ FITUR SERANGAN YANG MEMBUMIHANGUSKAN

    OSINT Brutal – whois, dnsrecon, gobuster dns, subdomain enumeration.

    Port scanning cepat – 15 port umum, lalu nmap service version.

    Web exploitation – sqlmap (full), nikto, LFI/RFI testing, admin panel brute dengan wordlist fasttrack.

    DDoS – Layer7 HTTP flood (50 thread), Layer4 SYN flood (raw socket).

    Ransomware simulasi – enkripsi AES (Fernet) terhadap file .txt, .doc, .pdf, .jpg, .py di /tmp.

    Reverse shell payload – base64 encoded bash reverse shell, siap pakai.

🔑 PERINTAH CEPAT
bash

# Install
sudo ./install_venom4.sh

# Run GUI
sudo python3 venom4.py

# Hanya defense (via terminal, tanpa GUI? edit saja worker)
python3 -c "from venom4 import VenomWorker; w = VenomWorker('defense'); w.run()"   # tapi lebih baik pakai GUI

📁 STRUKTUR OUTPUT (kalz_results/)

Setelah menjalankan attack, semua hasil disimpan di folder kalz_results/:

    whois.txt – data whois domain

    dns.csv – hasil dnsrecon

    subdomains.txt – daftar subdomain (gobuster dns)

    nmap.txt – service version dari port yang terbuka

    sqlmap/ – database hasil sqlmap

    nikto.txt – laporan nikto

    lfi.txt – daftar potensi LFI/RFI

    ransom_key.txt – kunci dekripsi (simulasi)

    revshell.txt – payload reverse shell

⚠️ PERINGATAN KERAS DARI KALZ

    Tool ini dibuat untuk tujuan edukasi keamanan siber dan pengujian sistem milik sendiri.
    Saya (Kalz) tidak bertanggung jawab atas penyalahgunaan.
    Jika digunakan untuk merusak sistem orang lain, Anda melanggar hukum dan berisiko dipenjara.
    Ingat: saya masih mencari pembully yang dulu mengejek nama saya.
    Jika Anda punya informasi tentang orang yang suka ngetawain nama "Kalz", lapor. Saya selesaikan.

🧬 LISENSI

UNLICENSE – Domain publik. Bebas digunakan, dimodifikasi, disebarkan. Tidak ada garansi. Anda bertanggung jawab penuh
## 📸 TAMPILAN ASLI GUI

<p align="center">
  <img src="venom_gui.png" width="800" alt="venom4 gui">
</p>
