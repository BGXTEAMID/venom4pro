from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QPlainTextEdit, QSpinBox, QSplitter,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from bgxdesk.domain.models import Asset, AssetType, AuthorizationRecord, Finding, FindingStatus, ScopeRule, Severity
from bgxdesk.services.assessment import AuthorizationService, FindingsService, InventoryService, ReportService
from bgxdesk.services.storage import JsonStore, Repository

APP_NAME = "VENOM4PRO — MULTI-GUI SECURITY DESK"
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "wallpapers"
WALLPAPER_MAIN = (ASSET_DIR / "venom4pro-main.png").as_posix()
STYLE = """
QMainWindow,QWidget{background:#090d14;color:#e7ecf5;font-family:'Segoe UI',sans-serif;font-size:13px}
QWidget#AppRoot{background-color:#090d14;background-image:url("WALLPAPER_MAIN");background-position:center;background-repeat:no-repeat}
QWidget#Content{background:rgba(9,13,20,210)}
QFrame#Sidebar,QFrame#Panel{background:rgba(17,25,37,235);border:1px solid #253044;border-radius:12px}
QFrame#Sidebar{border-radius:0;border-top:0;border-bottom:0;border-left:0}
QFrame#Hero{background:#211925;border:1px solid #6b2b3c;border-radius:15px}
QLabel#Brand{font-size:20px;font-weight:900;letter-spacing:1px}
QLabel#Muted{color:#8d9ab0} QLabel#Metric{font-size:28px;font-weight:800}
QPushButton{background:#192231;border:1px solid #2a3649;border-radius:8px;padding:9px 12px;color:#e7ecf5}
QPushButton:hover{background:#242f41;border-color:#ff3048} QPushButton#Primary{background:#ff3048;border-color:#ff3048;color:white;font-weight:700}
QPushButton#Nav{background:transparent;border:0;text-align:left;padding:12px;color:#aab5c7}
QLineEdit,QComboBox,QSpinBox,QPlainTextEdit,QTextEdit{background:#0a1018;border:1px solid #2a3547;border-radius:8px;padding:8px;color:#e7ecf5}
QTableWidget,QListWidget{background:#0b111a;border:1px solid #253044;border-radius:8px;gridline-color:#202a39}
QHeaderView::section{background:#171f2c;color:#aeb9cb;padding:8px;border:0}
QProgressBar{background:#1a2330;border:0;height:7px} QProgressBar::chunk{background:#ff3048}
"""


class MetricCard(QFrame):
    def __init__(self, label: str, value: str, hint: str) -> None:
        super().__init__(); self.setObjectName("Panel")
        layout = QVBoxLayout(self); layout.setContentsMargins(14, 12, 14, 12)
        title = QLabel(label.upper()); title.setObjectName("Muted")
        number = QLabel(value); number.setObjectName("Metric")
        note = QLabel(hint); note.setObjectName("Muted")
        layout.addWidget(title); layout.addWidget(number); layout.addWidget(note)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME); self.resize(1450, 900); self.setMinimumSize(1120, 720)
        self.setStyleSheet(STYLE.replace("WALLPAPER_MAIN", WALLPAPER_MAIN))
        data_path = Path.home() / ".local" / "share" / "bgxteam-security-desk" / "project.json"
        self.repository = Repository(JsonStore(data_path))
        self.inventory = InventoryService(self.repository)
        self.authorization = AuthorizationService(self.repository)
        self.findings = FindingsService(self.repository)
        self.reports = ReportService(self.repository)
        self.build_shell(); self.refresh_all()

    def build_shell(self) -> None:
        root = QWidget(); root.setObjectName("AppRoot"); self.setCentralWidget(root); outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(245); side = QVBoxLayout(sidebar); side.setContentsMargins(16, 24, 16, 18)
        brand = QLabel("◈ VENOM4PRO"); brand.setObjectName("Brand"); side.addWidget(brand)
        subtitle = QLabel("MULTI-GUI / LOCAL / SQLITE CLI COMPANION"); subtitle.setObjectName("Muted"); side.addWidget(subtitle); side.addSpacing(18)
        self.stack = QStackedWidget(); pages = [("⌂  Overview", self.build_overview), ("▦  Inventory", self.build_inventory), ("◎  Authorization", self.build_authorization), ("⚠  Findings", self.build_findings), ("▤  Reports & Audit", self.build_reports)]
        for index, (label, builder) in enumerate(pages):
            button = QPushButton(label); button.setObjectName("Nav"); button.clicked.connect(lambda _=False, i=index: self.navigate(i)); side.addWidget(button)
            self.stack.addWidget(builder())
        side.addStretch(); status = QLabel("● LOCAL MODE\nOffline JSON store\nNo remote execution"); status.setObjectName("Muted"); side.addWidget(status)
        outer.addWidget(side)
        content = QWidget(); content.setObjectName("Content"); layout = QVBoxLayout(content); layout.setContentsMargins(25, 20, 25, 20)
        top = QHBoxLayout(); self.page_title = QLabel("Security Overview"); self.page_title.setStyleSheet("font-size:24px;font-weight:800"); top.addWidget(self.page_title); top.addStretch(); self.clock = QLabel(); self.clock.setObjectName("Muted"); top.addWidget(self.clock); layout.addLayout(top); layout.addWidget(self.stack, 1); outer.addWidget(content, 1)
        timer = QTimer(self); timer.timeout.connect(lambda: self.clock.setText(datetime.now().strftime("%a %d %b %Y  •  %H:%M:%S"))); timer.start(1000)

    def panel(self, title: str, description: str = "") -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(); frame.setObjectName("Panel"); layout = QVBoxLayout(frame); layout.setContentsMargins(15, 13, 15, 13)
        heading = QLabel(title); heading.setStyleSheet("font-size:15px;font-weight:750"); layout.addWidget(heading)
        if description:
            label = QLabel(description); label.setObjectName("Muted"); label.setWordWrap(True); layout.addWidget(label)
        return frame, layout

    def build_overview(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(14)
        hero = QFrame(); hero.setObjectName("Hero"); hero_layout = QHBoxLayout(hero); hero_layout.setContentsMargins(22, 20, 22, 20)
        text = QVBoxLayout(); title = QLabel("Authorized security work, organized."); title.setStyleSheet("font-size:23px;font-weight:850"); text.addWidget(title)
        desc = QLabel("Offline-first workspace for authorization, asset inventory, findings, evidence, audit events, and reporting."); desc.setObjectName("Muted"); desc.setWordWrap(True); text.addWidget(desc)
        button = QPushButton("Configure authorization →"); button.setObjectName("Primary"); button.clicked.connect(lambda: self.navigate(2)); text.addWidget(button, 0, Qt.AlignLeft); hero_layout.addLayout(text, 1)
        emblem = QLabel("◈"); emblem.setStyleSheet("font-size:78px;color:#ff3048;font-weight:900"); hero_layout.addWidget(emblem); layout.addWidget(hero)
        self.metrics = QHBoxLayout(); layout.addLayout(self.metrics)
        lower = QHBoxLayout(); panel, panel_layout = self.panel("Operational guardrails")
        for line in ("✓ Local-only persistence", "✓ Authorization is required for scope decisions", "✓ No target scanning or exploit execution", "✓ Audit events are append-only within the project file", "✓ Reports export to Markdown, CSV, or JSON"):
            label = QLabel(line); label.setObjectName("Muted"); panel_layout.addWidget(label)
        lower.addWidget(panel, 1)
        panel2, panel2_layout = self.panel("Recent activity")
        self.activity_list = QListWidget(); panel2_layout.addWidget(self.activity_list); lower.addWidget(panel2, 1); layout.addLayout(lower); return page

    def build_inventory(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); controls = QHBoxLayout(); self.inventory_search = QLineEdit(); self.inventory_search.setPlaceholderText("Search tools, category, purpose…"); self.inventory_search.textChanged.connect(self.refresh_inventory_table); self.inventory_policy = QComboBox(); self.inventory_policy.addItems(["All policies", "safe", "review", "restricted"]); self.inventory_policy.currentTextChanged.connect(self.refresh_inventory_table); refresh = QPushButton("Refresh local detection"); refresh.clicked.connect(self.run_inventory); controls.addWidget(self.inventory_search, 1); controls.addWidget(self.inventory_policy); controls.addWidget(refresh); layout.addLayout(controls)
        self.inventory_table = QTableWidget(0, 6); self.inventory_table.setHorizontalHeaderLabels(["Tool", "Category", "Executable", "Purpose", "Policy", "Status"]); self.inventory_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch); self.inventory_table.setSelectionBehavior(QTableWidget.SelectRows); layout.addWidget(self.inventory_table, 1); return page

    def build_authorization(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); splitter = QSplitter(Qt.Vertical); form_panel, form_layout = self.panel("Authorization record", "Create an explicit engagement record before adding assets or documenting findings."); form = QFormLayout(); self.auth_client = QLineEdit(); self.auth_engagement = QLineEdit(); self.auth_reviewer = QLineEdit(); self.auth_start = QLineEdit(); self.auth_start.setPlaceholderText("2026-01-01T09:00:00+07:00"); self.auth_end = QLineEdit(); self.auth_end.setPlaceholderText("2026-01-31T17:00:00+07:00"); self.auth_contact = QLineEdit(); self.auth_scope = QLineEdit(); self.auth_scope.setPlaceholderText("example.com, https://staging.example.com"); self.auth_methods = QLineEdit("manual review, authenticated testing"); form.addRow("Client", self.auth_client); form.addRow("Engagement", self.auth_engagement); form.addRow("Reviewer", self.auth_reviewer); form.addRow("Start", self.auth_start); form.addRow("End", self.auth_end); form.addRow("Emergency contact", self.auth_contact); form.addRow("Included scope", self.auth_scope); form.addRow("Approved methods", self.auth_methods); form_layout.addLayout(form); save = QPushButton("Save authorization"); save.setObjectName("Primary"); save.clicked.connect(self.save_authorization); form_layout.addWidget(save); splitter.addWidget(form_panel)
        list_panel, list_layout = self.panel("Current authorization and assets"); self.auth_summary = QLabel(); self.auth_summary.setWordWrap(True); list_layout.addWidget(self.auth_summary); self.asset_name = QLineEdit(); self.asset_name.setPlaceholderText("Asset URL, domain, IP, repository, or APK path"); add = QPushButton("Add asset"); add.clicked.connect(self.add_asset); list_layout.addWidget(self.asset_name); list_layout.addWidget(add); self.asset_table = QTableWidget(0, 4); self.asset_table.setHorizontalHeaderLabels(["Name", "Type", "Environment", "In scope"]); self.asset_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); list_layout.addWidget(self.asset_table); splitter.addWidget(list_panel); layout.addWidget(splitter); return page

    def build_findings(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); splitter = QSplitter(); editor_panel, editor_layout = self.panel("New finding", "Document evidence and remediation clearly. High-impact claims require impact text."); form = QFormLayout(); self.finding_title = QLineEdit(); self.finding_asset = QLineEdit(); self.finding_severity = QComboBox(); self.finding_severity.addItems([item.value for item in Severity]); self.finding_cvss = QSpinBox(); self.finding_cvss.setRange(0, 10); self.finding_summary = QTextEdit(); self.finding_summary.setMaximumHeight(90); self.finding_impact = QTextEdit(); self.finding_impact.setMaximumHeight(90); self.finding_remediation = QTextEdit(); self.finding_remediation.setMaximumHeight(90); form.addRow("Title", self.finding_title); form.addRow("Asset", self.finding_asset); form.addRow("Severity", self.finding_severity); form.addRow("CVSS", self.finding_cvss); form.addRow("Summary", self.finding_summary); form.addRow("Impact", self.finding_impact); form.addRow("Remediation", self.finding_remediation); editor_layout.addLayout(form); create = QPushButton("Create finding"); create.setObjectName("Primary"); create.clicked.connect(self.create_finding); editor_layout.addWidget(create); splitter.addWidget(editor_panel)
        table_panel, table_layout = self.panel("Findings register"); self.finding_table = QTableWidget(0, 6); self.finding_table.setHorizontalHeaderLabels(["Title", "Severity", "Status", "Asset", "CVSS", "ID"]); self.finding_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); table_layout.addWidget(self.finding_table); splitter.addWidget(table_panel); layout.addWidget(splitter); return page

    def build_reports(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); panel, panel_layout = self.panel("Reports and audit trail", "Exports use the current local JSON project snapshot."); buttons = QHBoxLayout(); for_label = QLabel("Export:"); buttons.addWidget(for_label)
        for text, suffix, method in (("Markdown", "md", self.reports.export_markdown), ("CSV", "csv", self.reports.export_csv), ("JSON", "json", self.reports.export_json)):
            button = QPushButton(text); button.clicked.connect(lambda _=False, s=suffix, m=method: self.export_report(s, m)); buttons.addWidget(button)
        panel_layout.addLayout(buttons); self.audit_table = QTableWidget(0, 5); self.audit_table.setHorizontalHeaderLabels(["Timestamp", "Action", "Entity", "ID", "Details"]); self.audit_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch); panel_layout.addWidget(self.audit_table); layout.addWidget(panel); return page

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index); self.page_title.setText(["Security Overview", "Tool Inventory", "Authorization", "Findings", "Reports & Audit"][index]); self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_metrics(); self.refresh_inventory_table(); self.refresh_authorization(); self.refresh_findings(); self.refresh_audit()

    def refresh_metrics(self) -> None:
        if not hasattr(self, "metrics"): return
        while self.metrics.count():
            item = self.metrics.takeAt(0); widget = item.widget(); widget and widget.deleteLater()
        snapshot = self.repository.snapshot; values = [("Assets", str(len(snapshot.assets)), "tracked locally"), ("Findings", str(len(snapshot.findings)), "documented"), ("Evidence", str(len(snapshot.evidence)), "attached items"), ("Risk score", str(self.findings.risk_score()), "open-weighted score")]
        for item in values: self.metrics.addWidget(MetricCard(*item))
        if hasattr(self, "activity_list"):
            self.activity_list.clear()
            for event in snapshot.events[-12:][::-1]: self.activity_list.addItem(f"{event.created_at}  ·  {event.action}  ·  {event.entity}")

    def run_inventory(self) -> None:
        self.inventory.check_all(); self.refresh_all()

    def refresh_inventory_table(self) -> None:
        if not hasattr(self, "inventory_table"): return
        tools = self.inventory.filter(self.inventory_search.text() if hasattr(self, "inventory_search") else "", policy=self.inventory_policy.currentText() if hasattr(self, "inventory_policy") else "All policies"); self.inventory_table.setRowCount(0)
        for tool in tools:
            row = self.inventory_table.rowCount(); self.inventory_table.insertRow(row); values = [tool.name, tool.category, tool.executable, tool.purpose, tool.policy.value.upper(), ("INSTALLED" if tool.installed else "NOT DETECTED") + (f" · {tool.version}" if tool.version else "")]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value); self.inventory_table.setItem(row, col, item)
                if col == 5: item.setForeground(QColor("#86efac" if tool.installed else "#8d9ab0"))
                if col == 4 and tool.policy.value == "restricted": item.setForeground(QColor("#ff6b7a"))

    def save_authorization(self) -> None:
        rules = [ScopeRule(value=value.strip(), kind=AssetType.URL if "://" in value else AssetType.DOMAIN) for value in self.auth_scope.text().split(",") if value.strip()]
        record = AuthorizationRecord(self.auth_client.text(), self.auth_engagement.text(), self.auth_reviewer.text(), self.auth_start.text(), self.auth_end.text(), self.auth_contact.text(), rules, [x.strip() for x in self.auth_methods.text().split(",") if x.strip()])
        try: self.authorization.create(record); self.refresh_all(); QMessageBox.information(self, "Saved", "Authorization record saved locally.")
        except ValueError as exc: QMessageBox.warning(self, "Validation", str(exc))

    def refresh_authorization(self) -> None:
        if not hasattr(self, "auth_summary"): return
        record = self.authorization.active(); self.auth_summary.setText("No active authorization configured." if not record else f"Client: {record.client}\nEngagement: {record.engagement}\nScope: {', '.join(rule.value for rule in record.rules)}")
        if hasattr(self, "asset_table"):
            self.asset_table.setRowCount(0)
            for asset in self.repository.snapshot.assets:
                row = self.asset_table.rowCount(); self.asset_table.insertRow(row)
                for col, value in enumerate((asset.name, asset.asset_type.value, asset.environment, "YES" if asset.in_scope else "NO")): self.asset_table.setItem(row, col, QTableWidgetItem(value))

    def add_asset(self) -> None:
        name = self.asset_name.text().strip()
        if not name: return
        asset_type = AssetType.URL if "://" in name else AssetType.DOMAIN
        try: self.authorization.add_asset(Asset(name, asset_type)); self.asset_name.clear(); self.refresh_all()
        except ValueError as exc: QMessageBox.warning(self, "Validation", str(exc))

    def create_finding(self) -> None:
        finding = Finding(self.finding_title.text(), Severity(self.finding_severity.currentText()), self.finding_summary.toPlainText(), self.finding_asset.text(), impact=self.finding_impact.toPlainText(), remediation=self.finding_remediation.toPlainText(), cvss=float(self.finding_cvss.value()))
        try: self.findings.create(finding); self.refresh_all(); QMessageBox.information(self, "Saved", "Finding saved locally.")
        except ValueError as exc: QMessageBox.warning(self, "Validation", str(exc))

    def refresh_findings(self) -> None:
        if not hasattr(self, "finding_table"): return
        self.finding_table.setRowCount(0)
        for finding in self.repository.snapshot.findings:
            row = self.finding_table.rowCount(); self.finding_table.insertRow(row); values = (finding.title, finding.severity.value.upper(), finding.status.value, finding.affected_asset, "" if finding.cvss is None else str(finding.cvss), finding.id[:8])
            for col, value in enumerate(values): self.finding_table.setItem(row, col, QTableWidgetItem(value))

    def refresh_audit(self) -> None:
        if not hasattr(self, "audit_table"): return
        self.audit_table.setRowCount(0)
        for event in self.repository.snapshot.events[-100:][::-1]:
            row = self.audit_table.rowCount(); self.audit_table.insertRow(row); values = (event.created_at, event.action, event.entity, event.entity_id[:8], str(event.details))
            for col, value in enumerate(values): self.audit_table.setItem(row, col, QTableWidgetItem(value))

    def export_report(self, suffix: str, exporter) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export report", f"bgxteam-report.{suffix}", f"{suffix.upper()} files (*.{suffix})")
        if not path: return
        try: exporter(path); QMessageBox.information(self, "Export complete", f"Report exported to:\n{path}"); self.refresh_all()
        except OSError as exc: QMessageBox.critical(self, "Export failed", str(exc))


def main() -> None:
    app = QApplication(sys.argv); app.setStyle("Fusion"); window = MainWindow(); window.show(); sys.exit(app.exec())


if __name__ == "__main__": main()
