#!/bin/bash
# [»kalz pro Active!!«]
# VENOM4 FINAL INSTALLER – ANTI ERROR, UNBREAKABLE

set -e  # berhenti jika error fatal, tapi kita tangani ringan

RED='\033[1;31m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

echo -e "${RED}╔════════════════════════════════════════════╗${NC}"
echo -e "${RED}║   VENOM4 – UNBREAKABLE INSTALLER FINAL    ║${NC}"
echo -e "${RED}║         KALZ PRODUCTION – ANTI HUKUM      ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════╝${NC}"

if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[!] HARUS ROOT! GINAKAN: sudo $0${NC}"
   exit 1
fi

echo -e "${CYAN}[+] Update repository...${NC}"
apt update -y

# ========== 1. APT PACKAGES (SEMUA DARI REPO KALI) ==========
echo -e "${BLUE}[*] Menginstall apt packages...${NC}"
APT_PKGS=(
    python3-pip python3-dev python3-venv python3-full
    git curl wget net-tools iptables
    build-essential libssl-dev libffi-dev
    ruby ruby-dev nmap hydra whois
    golang-go
    python3-requests python3-cryptography python3-pyqt5 python3-scapy
)
for pkg in "${APT_PKGS[@]}"; do
    echo -e "${YELLOW} -> $pkg${NC}"
    apt install -y $pkg
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}   [+] berhasil${NC}"
    else
        echo -e "${RED}   [-] gagal, lanjut...${NC}"
    fi
done

# ========== 2. TAMBAHAN MODULE PYTHON YANG TIDAK ADA DI APT (PAKAI PIP --break-system-packages) ==========
echo -e "${BLUE}[*] Menginstall module Python via pip (override PEP 668)...${NC}"
# Catatan: JANGAN upgrade pip! langsung install module.

PIP_MODS=("cryptography" "PyQt5" "scapy")  # requests sudah dari apt, cryptography dan PyQt5 mungkin butuh versi baru
for mod in "${PIP_MODS[@]}"; do
    echo -e "${YELLOW} -> pip3 install $mod --break-system-packages${NC}"
    pip3 install $mod --break-system-packages
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}   [+] $mod berhasil${NC}"
    else
        echo -e "${RED}   [-] $mod gagal, coba apt install python3-$mod${NC}"
        apt install -y python3-$mod 2>/dev/null || true
    fi
done

# ========== 3. GIT TOOLS (NIKTO, SQLMAP, DNSRECON, GOBUSTER, WPSCAN) ==========
echo -e "${BLUE}[*] Menginstall tools dari git dan gem...${NC}"
mkdir -p /opt/venom4_tools

# nikto
if ! command -v nikto &> /dev/null; then
    echo -e "${YELLOW} -> nikto${NC}"
    git clone https://github.com/sullo/nikto.git /opt/venom4_tools/nikto
    ln -sf /opt/venom4_tools/nikto/nikto.pl /usr/local/bin/nikto
    chmod +x /usr/local/bin/nikto
fi

# sqlmap
if ! command -v sqlmap &> /dev/null; then
    echo -e "${YELLOW} -> sqlmap${NC}"
    git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /opt/venom4_tools/sqlmap
    ln -sf /opt/venom4_tools/sqlmap/sqlmap.py /usr/local/bin/sqlmap
    chmod +x /usr/local/bin/sqlmap
fi

# dnsrecon
if ! command -v dnsrecon &> /dev/null; then
    echo -e "${YELLOW} -> dnsrecon${NC}"
    git clone https://github.com/darkoperator/dnsrecon.git /opt/venom4_tools/dnsrecon
    pip3 install -r /opt/venom4_tools/dnsrecon/requirements.txt --break-system-packages
    ln -sf /opt/venom4_tools/dnsrecon/dnsrecon.py /usr/local/bin/dnsrecon
    chmod +x /usr/local/bin/dnsrecon
fi

# gobuster (via go)
if ! command -v gobuster &> /dev/null; then
    echo -e "${YELLOW} -> gobuster${NC}"
    go install github.com/OJ/gobuster/v3@latest
    ln -sf ~/go/bin/gobuster /usr/local/bin/gobuster
fi

# wpscan (via gem, fallback pip)
if ! command -v wpscan &> /dev/null; then
    echo -e "${YELLOW} -> wpscan${NC}"
    gem install wpscan
    if ! command -v wpscan &> /dev/null; then
        pip3 install wpscan --break-system-packages
    fi
fi

# SecLists wordlist
if [[ ! -d /usr/share/wordlists/seclists ]]; then
    echo -e "${YELLOW} -> SecLists (wordlist)${NC}"
    git clone https://github.com/danielmiessler/SecLists.git /usr/share/wordlists/seclists
fi

# fasttrack.txt symlink
if [[ ! -f /usr/share/wordlists/fasttrack.txt ]]; then
    ln -sf /usr/share/wordlists/seclists/Passwords/Common-Credentials/10-million-password-list-top-100.txt /usr/share/wordlists/fasttrack.txt 2>/dev/null || true
fi

echo -e "${GREEN}[+] INSTALASI SELESAI TANPA ERROR!${NC}"
echo -e "${CYAN}Jalankan VENOM4 dengan: sudo python3 venom4.py${NC}"

# Shortcut
cat > /usr/local/bin/venom4 << 'EOF'
#!/bin/bash
sudo python3 /root/venom4.py
EOF
chmod +x /usr/local/bin/venom4
echo -e "${GREEN}[+] Shortcut 'venom4' siap.${NC}"
