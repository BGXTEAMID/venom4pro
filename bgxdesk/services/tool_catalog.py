"""Curated 600+ cybersecurity tool catalog for local inventory and planning.

The catalog is metadata only. It never executes a tool, sends traffic, installs
packages, guesses credentials, or generates exploit payloads. Commands exposed
by this module are limited to presence/version/help/package inspection.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable
import re


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    category: str
    command: str
    package: str
    family: str
    purpose: str
    risk: str = "review"
    source: str = "curated"
    aliases: tuple[str, ...] = ()

    def safe_commands(self) -> dict[str, str]:
        executable = self.command
        return {
            "presence": f"command -v {executable}",
            "version": f"{executable} --version",
            "help": f"{executable} --help",
            "package": f"apt-cache policy {self.package}",
        }

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self); value["aliases"] = list(self.aliases); value["safe_commands"] = self.safe_commands(); return value


# Names are intentionally grouped so operators can filter a large catalog.
# Availability differs by Kali release, architecture, and optional repository.
_GROUPS: dict[str, tuple[str, ...]] = {
"OSINT and reconnaissance": "amass assetfinder recon-ng theHarvester subfinder findomain dnsrecon dnsenum fierce finalrecon spiderfoot photon sn0int maigret sherlock socialscan holehe h8mail reconspider metagoofil maltego casefile osrframework twint mopper email2phonenumber phoneinfoga username-anarchy cupp emailharvester linkedin2username github-search gitrob trufflehog gitleaks octosuite whatsmyname namechk knowem userrecon dnstwist urlcrazy massdns shuffledns puredns alterx dnsx hakrevdns chaos subjack subzy nuclei-templates gowitness eyewitness aquatone webanalyze whatweb wappalyzer-cli retire.js builtwith dnsdumpster crtsh certgraph certspotter censys-cli shodan-cli securitytrails-cli spyse-cli onyphe-cli binaryedge-cli urlscan-cli waybackurls gau gauplus hakrawler katana cariddi arjun paramspider uro unfurl anew qsreplace gf dalfox".split(),
"Network discovery and DNS": "nmap masscan rustscan naabu zmap unicornscan hping3 nping fping arping netdiscover arp-scan nbtscan smbmap crackmapexec netexec enum4linux enum4linux-ng rpcclient rpcinfo showmount snmpwalk snmp-check onesixtyone ike-scan ikeprobe sslscan sslyze testssl.sh tls-scan tlsenum o-saft ssldump p0f passive-dns dnstop dnscap dnstracer dmitry lbd amap thc-ipv6 ipv6calc sipvicious sipsak sngrep voiphopper enumiax svmap svwar svcrack dnschef dnsmasq bind9 host dig nslookup drill kdig whois rdap-client ipcalc sipscan subnetcalc cidrmerge mapcidr netmask route6 traceroute tcptraceroute tracepath mtr socat netcat ncat proxychains torsocks sshuttle chisel ligolo-ng frp rinetd iodine dnscat2 ptunnel ngrok cloudflared".split(),
"Web and HTTP assessment": "nikto wpscan joomscan droopescan cmsmap davtest cadaver feroxbuster gobuster dirsearch dirb dirbuster ffuf wfuzz hakrawler katana httpx httprobe httprobe-ng httpie curl wget aria2c lynx w3m links chromium firefox cutycapt wkhtmltoimage phantomjs playwright selenium zaproxy burpsuite mitmproxy proxify proxifier redsocks ssrfmap nosqli sqlmap commix tplmap dalfox xsser xsstrike beef-xss wapiti arachni skipfish whatweb wafw00f wafninja bypasswaf cloudfail wafw00f-ng smuggler request-smuggler http-request-smuggler desync-scan h2csmuggler h2spec h2load grpcurl grpcui websocat wscat websocketking websocket-client graphqlmap clairvoyance graphql-cop inql graphw00f graphinder jwt-tool jwt-cracker jwt-hack jws-tool oauth2-tool samlmap samlify corsy corscanner corsair corscan nuclei nikto2 webscarab paros ratproxy vega w3af arachni2 websploit xray kiterunner ffuf-scripts".split(),
"API and application testing": "postman insomnia hoppscotch bruno soapui soapstone wsdl2html burp-rest-api mitmproxy2 api-fuzzer api-diff api-schema-validator openapi-generator swagger-cli redocly-cli spectral dredd schemathesis api-dog apifox restler restler-fuzzer taurus cariddi arjun param-miner paramspider kiterunner forager jaeles nuclei-api api-cop api.audit api-fuzzing api-security-checker graphql-inspector graphql-voyager graphql-playground graphqurl gql-cli gqlgen hasura-cli postgrest-cli supabase-cli firebase-tools amplify-cli serverless sam cli cdk terraform pulumi crossplane kubectl helm argocd flux kustomize istioctl linkerd consul nomad vault-cli boundary-cli aws azure gcloud doctl hcloudctl oci-cli alibabacloud eksctl k9s popeye kube-bench kube-hunter kubeaudit kubescape trivy-grype syft cosign chainguard melange apko".split(),
"Vulnerability assessment": "openvas gvm greenbone nessus nessuscli nikto nuclei nmap-vulners vulners searchsploit cve-bin-tool cve-search cve-lookup cvechecker vulnix debsecan lynis tiger chkrootkit rkhunter unhide yara yara-python clamav freshclam sophos-scan maldet linux-exploit-suggester linux-smart-enumeration linpeas pspy lse unix-privesc-check windows-exploit-suggester wesng winpeas seatbelt powerup sharpup privesccheck got-your-six peass-ng exploitdb retire trivy grype osv-scanner osv-scanner-action dependency-check dependency-track safety pip-audit bandit semgrep codeql sonarqube sonar-scanner checkov terrascan tfsec cfn-nag kube-score polaris dockle hadolint ggshield horusec mobsf mobsfscan brakeman bundler-audit npm-audit yarn-audit pnpm-audit osv-detector snyk snyk-to-html dependabot-preview renovate osv-scanner alpine-secdb debian-security-support ubuntu-security-status".split(),
"Static analysis and code security": "semgrep semgrep-core codeql codeql-cli sonar-scanner sonarlint pyright mypy pylint flake8 ruff bandit black isort safety pip-audit pipdeptree pip-check poetry audit cargo-audit cargo-deny cargo-geiger clippy gosec govulncheck staticcheck golangci-lint govulncheck npm-audit yarn-audit pnpm-audit retire eslint eslint-security-plugin eslint-plugin-no-unsanitized typescript tsc biome deno lint rubocop brakeman bundler-audit rails-audit phpcs phpstan psalm composer-audit spotbugs pmd checkstyle detekt ktlint android-lint swiftlint oclint infer cppcheck flawfinder rats splint clang-tidy clang-analyzer coverity flawfinder vera++ sonarqube fortify checkmarx veracode snyk snyk-code deepfence threatmapper horusec klocwork cppdepend ndepend roslyn-analyzers security-code-scan secureflag".split(),
"Containers and DevSecOps": "docker podman nerdctl buildah skopeo crane regctl oras dive ctop lazydocker dockle trivy grype syft cosign notation cosign-installer docker-bench-security kube-bench kube-hunter kubeaudit kubescape kube-score kubevious popeye polaris starboard falco sysdig tracee tetragon cilium-cli helm helmfile kustomize kpt k9s kubectl kubectx kubens stern argocd argo-rollouts flux fluxctl istioctl linkerd consul nomad rancher-cli eksctl kind minikube k3d k3s microk8s talosctl clusterctl terraform terragrunt tofu pulumi ansible molecule chef-inspec inspec puppet bolt saltstack packer vagrant nomad-pack cloud-init checkov terrascan tfsec cfn-nag cfn-lint cdk-nag serverless sam awscli gcloud azure-cli azurite localstack motostack cloudmapper prowler scoutsuite cloudfox pacu cartography steampipe cloudcustodian cloudsploit kubeclarity syft bomctl bomber".split(),
"Password and authentication auditing": "john hashcat hashcat-utils hashcat-legacy hydra medusa ncrack patator thc-hydra crowbar crackmapexec netexec smbmap responder impacket-certipy impacket-getnpusers impacket-secretsdump impacket-psexec impacket-wmiexec impacket-smbexec impacket-ntlmrelayx impacket-mssqlclient impacket-GetUserSPNs impacket-GetNPUsers mimikatz pypykatz lsassy nanodump secretsdump pwdump pwdumpx fgdump samdump2 chntpw ophcrack rainbowcrack rcracki_mt crunch cewl cupp rsmangler mentalist princeprocessor statsprocessor maskprocessor kwprocessor combinator hashcat-utils rulegen hashcat-hctools passlib bcrypt-tool scrypt-tool argon2-cli mkpasswd htpasswd openssl passwd pwgen diceware apg mkpasswd ssh-audit sshkeys audit-users passwdqc cracklib johnny hashid hash-identifier name-that-hash haiti nth cyberchef offlinehashcat".split(),
"Wireless and 802.11": "aircrack-ng airmon-ng airodump-ng aireplay-ng airbase-ng airdecap-ng airdecloak-ng airgraph-ng besside-ng kismet wavemon wifite reaver bully pixiewps wash fern-wifi-cracker fluxion mdk4 mdk3 hostapd hostapd-wpe freeradius eaphammer wifiphisher wifi-pumpkin wifijammer bettercap hcxdumptool hcxpcapngtool hcxhash2cap hcxhashtool hcxkeys hcxmactool hcxpsktool hcxessidtool hcxeiutool hcxtools hcxcaptool pyrit cowpatty asleap cowpatty-ng wifiarsenal wifi-honey wifi-monitor wifite2 iw iwconfig iwlist rfkill macchanger mausezahn scapy pyrit2 gr-ieee802-11 gr-gsm gr-osmosdr airgeddon fluxion-ng roguehostap mana hostapd-mana wifipumpkin3 wifiphisher-ng wlan1 wifichannel".split(),
"Bluetooth RFID NFC SDR": "bluez bluetoothctl btmgmt btmon btscanner bluelog bluesnarfer blue_hydra bettercap gattacker blectf bleah blescan bluepy bleak btlejack crackle ubertooth ubertooth-btle ubertooth-rx ubertooth-specan gatttool hcitool rfkill rfcat killerbee zigdiggity zbstumbler zbassocfuzz zigbee2mqtt zigpy killerbee-ng nfcpy libnfc mfoc mfcuk mfterm nfc-list nfc-mfclassic proxmark3 proxmark3-client rfidler rfidtool flipperzero-cli hackrf hackrf_transfer hackrf_info rtl-sdr rtl_adsb rtl_433 gqrx gnuradio grgsm gr-gsm gr-scan gsm-rtl osmocom-bb osmo-trx kalibrate multimon-ng inspectrum sigint-suite sdrangel srsran openbts yate bladeRF lime-suite soapysdr airspy dump1090 readsb adsbexchange".split(),
"Hardware and IoT": "flashrom binwalk foremost strings hexdump xxd minicom screen picocom tio openocd jtagulator jtagenum jtag-hammer jtagulator2 urjtag gdb-multiarch qemu-system qemu-user unicorn capstone keystone angr avatar2 firmwalker firmware-mod-kit firmware-analysis-toolkit fact emba binwalk3 firmware-mod-kit2 routersploit routerhunter routerscan mirai-scanner iotmap iotsecfuzz boofuzz peach boofuzz-cli scapy scapy-radio bluetoothctl bluez wireshark tshark usbtop usbmon usbrip usbgrep libusb usbutils lsusb udevadm evtest hidapi hidattack plunderer badusb ducky-script rubber-ducky flipperzero qmk dfu-util teensy_loader_cli esptool stm32flash avrdude bossac rpiboot openocd pyftdi adafruit-blinka gpiozero wiringpi sigrok-cli pulseview logic2 saleae logic-analyzer sigrok-firmware".split(),
"Digital forensics and incident response": "autopsy sleuthkit fls mmls fsstat icat istat ifind blkls blkcat dls dcalc mmstat img_stat jcat sorter tsk_recover ewf-tools ewfinfo ewfmount ewfrecover ewfacquire afflib affinfo aff4imager dc3dd dcfldd ddrescue guymager testdisk photorec scalpel foremost bulk-extractor binwalk xxd strings exiftool mat2 pdfinfo pdfimages pdftotext oletools olevba oleid mraptor rtfobj peepdf pdf-parser didier stegoveritas stegseek steghide outguess zsteg binwalk yara yarGen yarascan volatility volatility3 rekall lime linux-memory-dump winpmem avml magnet-ram-capture dumpit fmem strings gcore procfs sysdig falco auditd ausearch aureport journalctl osquery grr osqueryi velociraptor kape kapeexe plaso log2timeline psort timeline explorer chainsaw hayabusa sigma-cli timesketch dfir-iris thehive cortex misp misp-modules cabby stix2-taxii splunk-cli elastic-agent elasticsearch kibana zeek suricata snort bro tcpdump tshark ngrep netsniff-ng xplico networkminer caploader pcapfix pcapng-tools".split(),
"Malware analysis and reverse engineering": "ghidra radare2 r2 cutter ida ida-free binary-ninja hopper objdump readelf nm strings file ldd patchelf elfutils eu-readelf eu-elflint elfparser pyelftools lief capstone keystone unicorn angr rizin rz-ghidra rz-bin rz-asm rz-run gdb gdb-multiarch lldb ollydbg x64dbg windbg immunities-debugger dnspy ilspy dotnet-dump dotnet-trace dnlib monodis ildasm apktool jadx dex2jar d8 baksmali smali androguard radare2cutter capa capa-rules floss floss-macho floss-pe pe-sieve hollows-hunter pefile lief yara yara-python yara-compiler vivisect miasm manticore triton symcc symqemu qiling emu86 bochs qemu unicorn-engine dynamorio frida frida-tools frida-trace frida-ps frida-discover objection rizin-signed pebear pefile-explorer pestudio pestudio-cli die Detect-It-Easy diec exiftool upx upx-ucl packerid unpacme de4dot dnspy dnlib dotpeek xpnova scdbg shellcode-fluctuation shellnoob msfvenom-shellcode-decoder donut sRDI donut-shellcode bin2bin objcopy cwe_checker retdec retdec-decompiler snowman ghidra-headless".split(),
"Mobile Android iOS": "adb fastboot scrcpy android-platform-tools apktool jadx dex2jar d8 baksmali smali androguard mobsf mobsfscan objection frida frida-tools frida-server r2frida drozer drozer-agent appium appium-doctor uiautomator2 mitmproxy mitmweb proxyman ios-deploy libimobiledevice idevice_id ideviceinfo ideviceinstaller iproxy checkra1n unc0ver palera1n objection-ios class-dump class-dump-z hopper ida arm-none-eabi-objdump otool ldid codesign codesign_allocate plutil simctl xcrun ios-deploy ios-deploy-cli mobSF apk-mitm uber-apk-signer apksigner zipalign bundletool aapt aapt2 axmlprinter apktool-cli jadx-gui enjarify dex2jar2 smali2java bytecode-viewer fernflower cfr procyon recaf android-studio gradle gradlew sdkmanager avdmanager emulator mlaunch ios-deploy frida-ios-dump frida-ios-dump2 bagbak ipatool palera1n-c".split(),
"Windows Active Directory": "impacket impacket-smbclient impacket-psexec impacket-wmiexec impacket-smbexec impacket-atexec impacket-dcomexec impacket-ntlmrelayx impacket-secretsdump impacket-getuserspns impacket-getnpusers impacket-lookupsid impacket-rpcdump impacket-samrdump impacket-regsecrets impacket-ticketconverter impacket-ticketer impacket-getst impacket-getnthash certipy certipy-ad bloodhound bloodhound-python sharphound bloodhound-ce netexec crackmapexec enum4linux enum4linux-ng smbmap smbclient rpcclient ldapsearch ldapdomaindump adfind adexplorer powerview powerup powermad seatbelt sharpup winpeas wesng windows-exploit-suggester windows-privesc-check winrm evil-winrm kerbrute rubeus kekeo mimikatz pypykatz lsassy nanodump procdump procdump64 handle autoruns sigcheck sysinternals sysmon sysmonview wevtutil logman xperf windbg cdb ntsd msfpc responder mitm6 inveigh ntlmrelayx coercer petitpotam printerbug dfscoerce shadowcoerce petitpotam2 smbrelayx smbserver.py pywerview ldapdomaindump adidnsdump adalanche manspider".split(),
"Traffic analysis and proxies": "wireshark tshark dumpcap capinfos editcap mergecap text2pcap reordercap randpkt rawshark tcpdump tcpflow tcpreplay tcprewrite netsniff-ng ngrep dsniff ettercap etterlog macchanger bettercap arpspoof sslstrip mitmproxy mitmweb mitmdump proxify proxifier burpsuite zaproxy paros webscarab ratproxy sslsplit ssldump tcpick chaosreader xplico networkminer caploader bro zeek suricata snort snort3 arkime moloch securityonion stenographer netscout ntopng nethogs iftop iptraf-ng bmon vnstat conntrack conntrack-tools nftables iptables ebtables arptables firewalld ufw wireguard-tools openvpn strongswan libreswan ike-scan stunnel socat ncat netcat proxychains torsocks sshuttle chisel ligolo-ng frp rinetd redsocks gost gost-rs".split(),
"Fuzzing and protocol testing": "boofuzz peach sulley spike bed boofuzz-cli afl afl++ honggfuzz libfuzzer radamsa zzuf sfuzz mangleme wfuzz ffuf gobuster dirsearch feroxbuster dirb dirbuster burp-intruder zap-fuzzer nuclei ffuf-fuzz ffuf-scripts wfuzz-scripts ffuf-x ffufplus turbo-intruder mitmproxy-fuzz restler schemathesis hypothesis pytest-fuzz atheris jazzer cargo-fuzz go-fuzz zzuf radamsa american-fuzzy-lop dumbfuzz peachfuzzer sulley2 kitty boofuzz-rest boofuzz-web boofuzz-mutators tlsfuzzer tls-attacker tlsmate h2spec h2fuzz quicly quic-go scapy fuzzowski legion w3af wpscan cmsmap joomscan droopescan davtest nikto wapiti skipfish arachni w3af-console sqlmap nosqlmap nosqli commix tplmap ssrfmap x8 x8r arjun paramspider".split(),
"Crypto stego and privacy": "openssl gpg gpg2 age sops minisign signify cosign step-cli cfssl easyrsa certbot acme.sh lego dehydrated mkcert step-ca cryptsetup veracrypt truecrypt tomb luks cryptsetup-reencrypt hashcat john hashid hash-identifier haiti name-that-hash cyberchef cyberchef-cli ciphey dcode hashcat-utils pass-the-hash hashdeep md5deep sha256deep ssdeep fuzzyhash tlsh sdhash rhash rhash-cli steghide stegseek outguess zsteg stegoveritas openstego silenteye cloak snow ascii2hex base64 xxd hexdump qrencode zbarimg exiftool mat2 metadata-cleaner onionshare tor torsocks proxychains i2p i2pd freenet lokinet privoxy mixminion nyx obfs4proxy snowflake meek shadowsocks v2ray xray sing-box wireguard openvpn age yubikey-manager ykman nitrokey-app keepassxc bitwarden-cli pass gopass scrypt argon2 bcrypt sops age-plugin-yubikey".split(),
"Reporting case management and governance": "dradis faraday faraday-cli serge pwncat reportlab pandoc wkhtmltopdf weasyprint typst obsidian logseq notion-cli thehive cortex misp misp-modules opencti opencti-client threat-dragon threatdragon drawio graphviz mermaid-cli plantuml d2 asciidoctor sphinx mkdocs hugo jekyll quarto quarto-cli pandoc-citeproc csvkit miller jq yq gron dasel jd visidata csvkit xsv sqlitebrowser litecli usql pgcli mycli inxi neofetch screenfetch fastfetch glances bpytop btop htop tmux zellij screen shellcheck shfmt bats pytest tox nox pre-commit just make task act".split(),
"System administration and defensive utilities": "psutil procps sysstat lsof strace ltrace dstat iotop iostat vmstat sar free top htop btop bmon dmesg journalctl systemctl service chkconfig cron crontab at batch anacron logrotate rsyslog syslog-ng auditd apparmor_parser aa-status selinux semodule getenforce ufw firewalld nft iptables ip6tables ebtables arptables conntrack fail2ban aide tripwire tiger lynis chkrootkit rkhunter unhide debsums debsecan apt-file dpkg-query apt-cache apt-show-versions needrestart unattended-upgrades timeshift restic borg borgmatic rclone rsync duplicity tar cpio pax zip unzip 7z zstd lz4 pigz pv gnuplot gawk sed awk grep ripgrep fd fzf bat exa eza findutils coreutils util-linux procps-ng".split(),
"CTF and training labs": "metasploitable dvwa juice-shop webgoat mutillidae bWAPP vulnerable-web-applications-vwa hackazon badstore damn-vulnerable-node-application damn-vulnerable-web-application vulhub vulnserver owasp-crs owasp-zap-baseline insecurebankv2 insecure-flag-goat crapi cr0wnr dctf pwnable pwntools pwndbg gef peda ropper ropgadget one_gadget angr manticore z3-solver gdb ghidra radare2 cutter checksec seccomp-tools libc-database patchelf elfutils pwntools-template qemu-user qemu-system docker podman vagrant virtualbox vmware-vdiskmanager chisel socat netcat nmap tcpdump wireshark metasploit-framework msfconsole msfvenom msfdb searchsploit exploitdb seclists wordlists rockyou crunch cewl john hashcat hydra sqlmap burpsuite zaproxy ffuf gobuster nikto nuclei wpscan responder impacket bloodhound certipy".split(),
}


def _build() -> tuple[CatalogEntry, ...]:
    entries: list[CatalogEntry] = []
    seen: set[str] = set()
    restricted_categories = {"Password and authentication auditing", "CTF and training labs", "Windows Active Directory", "Web and HTTP assessment", "Fuzzing and protocol testing"}
    safe_categories = {"Reporting case management and governance", "System administration and defensive utilities", "Static analysis and code security", "Digital forensics and incident response"}
    for category, names in _GROUPS.items():
        for raw in names:
            name = raw.strip().lower()
            if not name or name in seen: continue
            seen.add(name)
            command = name.replace(" ", "-")
            package = command
            if command.endswith(".py"): package = command[:-3]
            family = "apt"
            if command in {"pip-audit", "bandit", "semgrep", "safety", "pwntools", "frida-tools", "cve-bin-tool"}: family = "pipx"
            elif command in {"cargo-audit", "cargo-deny", "cargo-geiger", "ripgrep", "fd", "bat", "zellij", "tokei"}: family = "cargo"
            elif command in {"gosec", "govulncheck", "staticcheck", "gopls"}: family = "go"
            elif command in {"npm-audit", "yarn-audit", "pnpm-audit", "eslint", "retire", "prettier"}: family = "npm"
            elif command in {"brakeman", "bundler-audit", "rubocop"}: family = "gem"
            elif command in {"terraform", "tofu", "terragrunt", "packer", "consul", "nomad", "vault-cli"}: family = "hashicorp"
            risk = "safe" if category in safe_categories else "restricted" if category in restricted_categories else "review"
            purpose = f"{category} utility; inspect availability and documentation before authorized use"
            entries.append(CatalogEntry(name, category, command, package, family, purpose, risk, "curated-security-catalog"))
    return tuple(entries)


CATALOG: tuple[CatalogEntry, ...] = _build()


def catalog() -> tuple[CatalogEntry, ...]: return CATALOG


def count() -> int: return len(CATALOG)


def categories() -> list[str]: return sorted({entry.category for entry in CATALOG})


def find(query: str = "", category: str | None = None, risk: str | None = None) -> list[CatalogEntry]:
    text = query.strip().lower()
    return [entry for entry in CATALOG if (not text or text in entry.name or text in entry.command or text in entry.purpose) and (not category or entry.category.lower() == category.lower()) and (not risk or entry.risk == risk)]


def category_counts() -> dict[str, int]:
    result: dict[str, int] = {}
    for entry in CATALOG: result[entry.category] = result.get(entry.category, 0) + 1
    return dict(sorted(result.items()))


def to_jsonable(entries: Iterable[CatalogEntry] | None = None) -> list[dict[str, Any]]: return [entry.as_dict() for entry in (entries if entries is not None else CATALOG)]


def safe_command_matrix(entry: CatalogEntry) -> list[str]: return list(entry.safe_commands().values())
