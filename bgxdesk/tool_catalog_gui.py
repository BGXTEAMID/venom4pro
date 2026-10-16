"""Standalone PySide6 GUI for the Venom4pro security-tool catalog.

This window is metadata-only: it never executes catalog tools or target
commands. Operators can search, filter, inspect safe probes, copy commands for
manual review, and export selected metadata.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView,
        QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
        QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - depends on host desktop
    if exc.name == "PySide6":
        raise
    raise

from bgxdesk.services.tool_catalog import CatalogEntry, categories, count, find, to_jsonable


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "wallpapers"
WALLPAPER = (ASSET_DIR / "venom4pro-wide.png").as_posix()

STYLE = f"""
QMainWindow,QWidget{{background:#070b12;color:#e8edf6;font-family:'Segoe UI',sans-serif;font-size:13px}}
QWidget#Root{{background-color:#070b12;background-image:url('{WALLPAPER}');background-position:center;background-repeat:no-repeat}}
QFrame#Sidebar,QFrame#Panel{{background:rgba(11,18,30,238);border:1px solid #26354c;border-radius:14px}}
QFrame#Sidebar{{border-radius:0;border-top:0;border-bottom:0;border-left:0}}
QLabel#Brand{{font-size:22px;font-weight:900;letter-spacing:2px;color:#ff3d56}}
QLabel#Title{{font-size:24px;font-weight:850}}
QLabel#Muted{{color:#9aa8bc}}
QLabel#Count{{font-size:17px;font-weight:800;color:#ff7081}}
QPushButton{{background:#172335;border:1px solid #2d405c;border-radius:8px;padding:9px 12px;color:#e8edf6}}
QPushButton:hover{{background:#22334b;border-color:#ff3d56}}
QPushButton#Primary{{background:#ff304b;border-color:#ff304b;color:#fff;font-weight:800}}
QLineEdit,QComboBox,QTextEdit{{background:#09111d;border:1px solid #2d405c;border-radius:8px;padding:8px;color:#e8edf6}}
QTableWidget,QListWidget{{background:rgba(5,10,17,245);border:1px solid #26354c;border-radius:9px;gridline-color:#1c2b3e}}
QHeaderView::section{{background:#172335;color:#c4d0df;padding:8px;border:0}}
"""


class ToolCatalogWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VENOM4PRO — TOOL CATALOG")
        self.resize(1500, 920)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(STYLE)
        self.visible_entries: list[CatalogEntry] = []
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        root = QWidget(); root.setObjectName("Root"); self.setCentralWidget(root)
        shell = QHBoxLayout(root); shell.setContentsMargins(0, 0, 0, 0); shell.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(270); side = QVBoxLayout(sidebar); side.setContentsMargins(18, 26, 18, 20)
        brand = QLabel("◈ VENOM4PRO"); brand.setObjectName("Brand"); side.addWidget(brand)
        subtitle = QLabel("TOOL CATALOG / LOCAL GUI"); subtitle.setObjectName("Muted"); side.addWidget(subtitle); side.addSpacing(22)
        scope = QLabel("CATALOG SCOPE"); scope.setObjectName("Muted"); side.addWidget(scope)
        self.count_label = QLabel("0 tools"); self.count_label.setObjectName("Count"); side.addWidget(self.count_label)
        self.category_count = QLabel("0 categories"); self.category_count.setObjectName("Muted"); side.addWidget(self.category_count); side.addSpacing(20)
        side.addWidget(QLabel("RISK POLICY"))
        risk_note = QLabel("SAFE\nInspection-only commands\n\nREVIEW\nHuman authorization required\n\nRESTRICTED\nMetadata only; no execution")
        risk_note.setObjectName("Muted"); risk_note.setWordWrap(True); side.addWidget(risk_note)
        side.addStretch()
        disclaimer = QLabel("No command execution\nNo target traffic\nNo exploit payloads")
        disclaimer.setObjectName("Muted"); side.addWidget(disclaimer)
        shell.addWidget(sidebar)

        content = QWidget(); layout = QVBoxLayout(content); layout.setContentsMargins(25, 20, 25, 20); layout.setSpacing(12)
        header = QHBoxLayout(); title = QLabel("Cybersecurity Tool Catalog"); title.setObjectName("Title"); header.addWidget(title); header.addStretch(); self.status_label = QLabel("Ready"); self.status_label.setObjectName("Muted"); header.addWidget(self.status_label); layout.addLayout(header)
        intro = QLabel("Search and review the unified catalog. The GUI only displays metadata and safe inspection commands such as command -v, --version, --help, and apt-cache policy."); intro.setObjectName("Muted"); intro.setWordWrap(True); layout.addWidget(intro)

        filters = QHBoxLayout(); self.search = QLineEdit(); self.search.setPlaceholderText("Search name, command, category, or purpose…"); self.search.textChanged.connect(self.refresh); self.category = QComboBox(); self.category.addItem("All categories"); self.category.addItems(categories()); self.category.currentTextChanged.connect(self.refresh); self.risk = QComboBox(); self.risk.addItems(["All risk levels", "safe", "review", "restricted"]); self.risk.currentTextChanged.connect(self.refresh); refresh_button = QPushButton("Refresh"); refresh_button.clicked.connect(self.refresh); export_button = QPushButton("Export JSON"); export_button.setObjectName("Primary"); export_button.clicked.connect(self.export_json); filters.addWidget(self.search, 1); filters.addWidget(self.category); filters.addWidget(self.risk); filters.addWidget(refresh_button); filters.addWidget(export_button); layout.addLayout(filters)

        splitter = QSplitter(Qt.Horizontal); table_panel = QFrame(); table_panel.setObjectName("Panel"); table_layout = QVBoxLayout(table_panel); self.table = QTableWidget(0, 6); self.table.setHorizontalHeaderLabels(["Tool", "Category", "Command", "Family", "Risk", "Package"]); self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection); self.table.itemSelectionChanged.connect(self.show_selected); table_layout.addWidget(self.table); splitter.addWidget(table_panel)
        detail_panel = QFrame(); detail_panel.setObjectName("Panel"); detail_layout = QVBoxLayout(detail_panel); detail_layout.addWidget(QLabel("Tool detail")); self.detail_title = QLabel("Select a catalog entry"); self.detail_title.setObjectName("Title"); detail_layout.addWidget(self.detail_title); self.detail = QTextEdit(); self.detail.setReadOnly(True); detail_layout.addWidget(self.detail, 1); self.copy_button = QPushButton("Copy selected safe command"); self.copy_button.clicked.connect(self.copy_command); self.copy_button.setEnabled(False); detail_layout.addWidget(self.copy_button); splitter.addWidget(detail_panel); splitter.setSizes([930, 430]); layout.addWidget(splitter, 1)
        shell.addWidget(content, 1)

    def current_filters(self) -> tuple[str, str | None, str | None]:
        query = self.search.text().strip(); category = self.category.currentText(); risk = self.risk.currentText(); return query, None if category == "All categories" else category, None if risk == "All risk levels" else risk

    def refresh(self) -> None:
        query, category, risk = self.current_filters(); self.visible_entries = find(query, category, risk); self.table.setRowCount(0)
        for entry in self.visible_entries:
            row = self.table.rowCount(); self.table.insertRow(row); values = (entry.name, entry.category, entry.command, entry.family, entry.risk.upper(), entry.package)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value)); self.table.setItem(row, column, item)
                if column == 4: item.setForeground(QColor("#86efac" if entry.risk == "safe" else "#ffcf70" if entry.risk == "review" else "#ff7180"))
        self.count_label.setText(f"{len(self.visible_entries)} / {count()} tools"); self.category_count.setText(f"{len(categories())} categories"); self.status_label.setText(f"Showing {len(self.visible_entries)} matching entries")
        if self.visible_entries: self.table.selectRow(0)
        else: self.clear_detail()

    def selected_entry(self) -> CatalogEntry | None:
        row = self.table.currentRow(); return self.visible_entries[row] if 0 <= row < len(self.visible_entries) else None

    def show_selected(self) -> None:
        entry = self.selected_entry()
        if not entry: self.clear_detail(); return
        self.detail_title.setText(entry.name)
        commands = entry.safe_commands(); lines = [f"Category: {entry.category}", f"Command: {entry.command}", f"Package: {entry.package}", f"Family: {entry.family}", f"Risk: {entry.risk.upper()}", "", entry.purpose, "", "Safe command matrix:", ""]
        lines.extend(f"{label}: {command}" for label, command in commands.items()); self.detail.setPlainText("\n".join(lines)); self.copy_button.setEnabled(True)

    def clear_detail(self) -> None: self.detail_title.setText("Select a catalog entry"); self.detail.clear(); self.copy_button.setEnabled(False)

    def copy_command(self) -> None:
        entry = self.selected_entry()
        if not entry: return
        command = entry.safe_commands()["presence"]; QApplication.clipboard().setText(command); self.status_label.setText(f"Copied safe inspection command: {command}")

    def export_json(self) -> None:
        if not self.visible_entries: QMessageBox.information(self, "Export", "No matching entries to export."); return
        path, _ = QFileDialog.getSaveFileName(self, "Export catalog JSON", "venom4pro-tools.json", "JSON files (*.json)")
        if not path: return
        Path(path).write_text(json.dumps(to_jsonable(self.visible_entries), ensure_ascii=False, indent=2), encoding="utf-8"); self.status_label.setText(f"Exported {len(self.visible_entries)} entries to {path}")


def main() -> None:
    app = QApplication(sys.argv); app.setStyle("Fusion"); window = ToolCatalogWindow(); window.show(); sys.exit(app.exec())


if __name__ == "__main__": main()
