"""PySide6 desktop view of the Kobra Banjir path-finding simulation.

Usage (from the repository root):
    python -m visual.qt_app
    python -m visual.qt_app cases/scenarios/case_01_kobra_banjir.yaml

Shortcuts: Left/Right step, Space play/pause, Home/End jump, F fit, Ctrl+O open.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from config.settings import CASES_DIR, DEFAULT_YAML_SCENARIO
from visual.canvas import (
    CompassOverlay,
    GraphRenderer,
    GraphView,
    LegendOverlay,
    ScaleBarOverlay,
)
from visual.info_panel import InfoPanel
from visual.scenarios import load_scenario_sources, source_from_path
from visual.snapshots import (
    ScenarioView,
    build_scenario_view_from_data,
)
from visual.timeline import StepTimeline

SPEEDS = [("Lambat", 2200), ("Normal", 1300), ("Cepat", 700)]


def apply_light_theme(app: QApplication) -> None:
    """Force a consistent light palette so dark Windows themes stay readable."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#ffffff"))
    palette.setColor(QPalette.WindowText, QColor("#263238"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f4f7fb"))
    palette.setColor(QPalette.Text, QColor("#263238"))
    palette.setColor(QPalette.Button, QColor("#f9fbfd"))
    palette.setColor(QPalette.ButtonText, QColor("#263238"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#4f46e5"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#263238"))
    palette.setColor(QPalette.PlaceholderText, QColor("#90a4ae"))
    palette.setColor(QPalette.Link, QColor("#4f46e5"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#9e9e9e"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#9e9e9e"))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#9e9e9e"))
    app.setPalette(palette)
    app.setStyleSheet(
        "QToolTip { background:#ffffff; color:#263238; border:1px solid #dbe3ec;"
        " padding:4px; }"
    )


class MainWindow(QMainWindow):
    def __init__(self, scenario_path: Path):
        super().__init__()
        application = QApplication.instance()
        if isinstance(application, QApplication):
            apply_light_theme(application)
        self.setWindowTitle("Kobra Banjir \u2014 Visualisasi Jalur Aman")
        self.resize(1280, 780)

        self.scenario_path = scenario_path
        self.view_data: Optional[ScenarioView] = None
        self.current_source: Optional[dict] = None
        self.current_id = scenario_path.stem
        self.sources: dict = {}
        self.current = 0
        self.playing = False
        self._fit_pending = True

        self.scene = QGraphicsScene(self)
        self.graph_view = GraphView(self.scene, self)
        self.renderer = GraphRenderer(self.scene, on_node_click=self._on_node_clicked)
        self.legend = LegendOverlay(self.graph_view)
        self.graph_view.legend_widget = self.legend
        self.compass = CompassOverlay(self.graph_view)
        self.graph_view.compass_widget = self.compass
        self.scale_bar = ScaleBarOverlay(self.graph_view)
        self.graph_view.scale_widget = self.scale_bar
        self.graph_view.place_overlays()
        self.legend.raise_()
        self.compass.raise_()
        self.scale_bar.raise_()

        self.info_panel = InfoPanel()
        self.info_scroll = QScrollArea()
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setFrameShape(QFrame.NoFrame)
        self.info_scroll.setWidget(self.info_panel)

        self.timeline = StepTimeline()
        self.timeline.step_selected.connect(self.set_current)

        self.prev_btn = QPushButton("\u25c0")
        self.next_btn = QPushButton("\u25b6")
        self.play_btn = QPushButton("\u25b6 Putar")
        self.speed_combo = QComboBox()
        for label, ms in SPEEDS:
            self.speed_combo.addItem(label, ms)
        self.speed_combo.setCurrentIndex(1)
        self.step_label = QLabel("\u2014")
        self.step_label.setStyleSheet("color:#607d8b; font-size:11px;")

        for button in (self.prev_btn, self.next_btn, self.play_btn):
            button.setFocusPolicy(Qt.NoFocus)
        self.prev_btn.setFixedWidth(38)
        self.next_btn.setFixedWidth(38)
        self.prev_btn.clicked.connect(lambda: self.set_current(self.current - 1))
        self.next_btn.clicked.connect(lambda: self.set_current(self.current + 1))
        self.play_btn.clicked.connect(self.toggle_play)

        controls = QHBoxLayout()
        controls.setContentsMargins(12, 6, 12, 4)
        controls.setSpacing(6)
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addSpacing(10)
        speed_label = QLabel("Kecepatan")
        speed_label.setStyleSheet("color:#78909c; font-size:11px;")
        controls.addWidget(speed_label)
        controls.addWidget(self.speed_combo)
        controls.addStretch(1)
        controls.addWidget(self.step_label)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self.graph_view, 1)
        left_layout.addLayout(controls)
        left_layout.addWidget(self.timeline)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.info_scroll)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([900, 380])
        self.setCentralWidget(splitter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_play)

        self._build_toolbar()
        self._build_shortcuts()
        self.statusBar().showMessage(
            "Gulir: zoom  \u00b7  Seret: geser  \u00b7  \u2190/\u2192: langkah  "
            "\u00b7  Spasi: putar  \u00b7  F: fit  \u00b7  Klik node: lihat label"
        )
        self._populate_scenarios()
        self.load_scenario(scenario_path)

    # ------------------------------------------------------------------ chrome
    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Utama")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setStyleSheet(
            "QToolBar { background:#ffffff; border-bottom:1px solid #e5ebf2;"
            " padding:4px 8px; spacing:6px; }"
            "QPushButton { padding:5px 10px; border:1px solid #dbe3ec;"
            " border-radius:6px; background:#f9fbfd; color:#263238; }"
            "QPushButton:hover { background:#eef2ff; border-color:#c7d2fe; }"
            "QPushButton:disabled { color:#b0bec5; background:#f2f5f8;"
            " border-color:#e5ebf2; }"
            "QComboBox { padding:4px 8px; border:1px solid #dbe3ec;"
            " border-radius:6px; background:#f9fbfd; color:#263238;"
            " min-width:260px; }"
        )
        self.addToolBar(toolbar)

        scenario_label = QLabel("Skenario  ")
        scenario_label.setStyleSheet("color:#607d8b; font-size:11px;")
        toolbar.addWidget(scenario_label)

        self.scenario_combo = QComboBox()
        self.scenario_combo.currentIndexChanged.connect(self._on_scenario_combo)
        toolbar.addWidget(self.scenario_combo)

        reload_btn = QPushButton("Muat ulang")
        reload_btn.clicked.connect(self._reload_current)
        toolbar.addWidget(reload_btn)

        open_btn = QPushButton("Buka\u2026")
        open_btn.clicked.connect(self._open_dialog)
        toolbar.addWidget(open_btn)

        toolbar.addSeparator()
        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self.graph_view.fit_scene)
        toolbar.addWidget(fit_btn)

        export_btn = QPushButton("Ekspor PNG")
        export_btn.clicked.connect(self._export_png)
        toolbar.addWidget(export_btn)

        self.network_btn = QPushButton("Jaringan OSM")
        self.network_btn.setCheckable(True)
        self.network_btn.setChecked(True)
        self.network_btn.setToolTip(
            "Tampilkan jalan sekitar hasil fetch Overpass"
        )
        self.network_btn.toggled.connect(self._toggle_network)
        toolbar.addWidget(self.network_btn)

        toolbar.addSeparator()
        algorithm = QLabel("Algoritma: Dijkstra")
        algorithm.setStyleSheet("color:#90a4ae; font-size:11px;")
        toolbar.addWidget(algorithm)

    def _build_shortcuts(self) -> None:
        bindings = [
            ("Left", lambda: self.set_current(self.current - 1)),
            ("Right", lambda: self.set_current(self.current + 1)),
            ("Space", self.toggle_play),
            ("Home", lambda: self.set_current(0)),
            ("End", lambda: self.set_current(len(self.view_data.snapshots) - 1)
             if self.view_data else None),
            ("F", self.graph_view.fit_scene),
            ("Ctrl+O", self._open_dialog),
        ]
        for sequence, handler in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(handler)

    # -------------------------------------------------------------------- data
    def _populate_scenarios(self) -> None:
        sources = load_scenario_sources()
        self.sources = {source["key"]: source for source in sources}
        self.scenario_combo.blockSignals(True)
        self.scenario_combo.clear()
        for source in sources:
            self.scenario_combo.addItem(source["title"], source["key"])
        self.scenario_combo.blockSignals(False)

    def _on_scenario_combo(self, index: int) -> None:
        key = self.scenario_combo.itemData(index)
        source = self.sources.get(key)
        if source is not None:
            self._load_source(source)

    def _open_dialog(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Pilih skenario", str(CASES_DIR), "Skenario YAML (*.yaml *.yml)"
        )
        if filename:
            self.load_scenario(Path(filename))

    def load_scenario(self, path: Path) -> None:
        try:
            source = source_from_path(Path(path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Gagal memuat skenario", str(exc))
            return
        self.sources[source["key"]] = source
        self._load_source(source)

    def _load_source(self, source: dict) -> None:
        try:
            data = build_scenario_view_from_data(source["data"], source["path"])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Gagal memuat skenario", str(exc))
            return

        self.view_data = data
        self.current_source = source
        self.scenario_path = Path(source["path"])
        self.current_id = data.metadata.get("case_id") or source["key"]
        self.current = 0
        self.playing = False
        self.timer.stop()
        self.play_btn.setText("\u25b6 Putar")

        self.setWindowTitle(
            f"Kobra Banjir \u2014 {data.metadata.get('title', source['title'])}"
        )
        has_network = bool(data.network_edges)
        self.network_btn.setEnabled(has_network)
        self.legend.set_network_visible(
            has_network and self.network_btn.isChecked()
        )
        self.compass.setVisible(not data.abstract)
        self.scale_bar.setVisible(not data.abstract)
        self.graph_view.place_overlays()
        self._sync_combo(source["key"])
        self.info_panel.set_view(data)
        self.timeline.set_snapshots(data.snapshots)
        self._fit_pending = True
        self._render()

    def _sync_combo(self, key: str) -> None:
        self.scenario_combo.blockSignals(True)
        index = -1
        for position in range(self.scenario_combo.count()):
            if self.scenario_combo.itemData(position) == key:
                index = position
                break
        if index < 0 and self.current_source is not None:
            self.scenario_combo.addItem(self.current_source["title"], key)
            index = self.scenario_combo.count() - 1
        if index >= 0:
            self.scenario_combo.setCurrentIndex(index)
        self.scenario_combo.blockSignals(False)

    def _reload_current(self) -> None:
        key = self.current_source["key"] if self.current_source else None
        self._populate_scenarios()
        source = self.sources.get(key) if key else None
        if source is None:
            source = next(iter(self.sources.values()), None)
        if source is not None:
            self._load_source(source)

    # ---------------------------------------------------------------- playback
    def set_current(self, index: int) -> None:
        if not self.view_data or not self.view_data.snapshots:
            return
        index = max(0, min(index, len(self.view_data.snapshots) - 1))
        if index == self.current:
            return
        self.current = index
        self._render()

    def toggle_play(self) -> None:
        if not self.view_data or len(self.view_data.snapshots) < 2:
            return
        self.playing = not self.playing
        if self.playing:
            if self.current >= len(self.view_data.snapshots) - 1:
                self.set_current(0)
            self.timer.setInterval(int(self.speed_combo.currentData()))
            self.timer.start()
            self.play_btn.setText("\u23f8 Jeda")
        else:
            self.timer.stop()
            self.play_btn.setText("\u25b6 Putar")

    def _advance_play(self) -> None:
        if not self.view_data:
            self.timer.stop()
            return
        if self.current >= len(self.view_data.snapshots) - 1:
            self.timer.stop()
            self.playing = False
            self.play_btn.setText("\u25b6 Putar")
            return
        self.set_current(self.current + 1)

    # ----------------------------------------------------------------- drawing
    def _render(self) -> None:
        if not self.view_data or not self.view_data.snapshots:
            return
        snapshot = self.view_data.snapshots[self.current]
        self.renderer.render(self.view_data, snapshot)
        self.info_panel.set_snapshot(snapshot)
        self.timeline.set_current(self.current)
        self.prev_btn.setEnabled(self.current > 0)
        self.next_btn.setEnabled(self.current < len(self.view_data.snapshots) - 1)
        self.step_label.setText(
            f"Keadaan {self.current + 1} dari {len(self.view_data.snapshots)}"
        )
        if self._fit_pending:
            self._fit_pending = False
            QTimer.singleShot(0, self.graph_view.fit_scene)

    # ----------------------------------------------------------------- actions
    def _on_node_clicked(self, node: dict) -> None:
        self.statusBar().showMessage(
            f"Node {node['id']}: {node.get('label', '')}", 6000
        )

    def _toggle_network(self, checked: bool) -> None:
        self.renderer.show_network = checked
        has_network = bool(self.view_data and self.view_data.network_edges)
        self.legend.set_network_visible(checked and has_network)
        self.legend.place()
        self._render()

    def _export_png(self) -> None:
        if not self.view_data:
            return
        default = f"{self.current_id}_keadaan_{self.current + 1}.png"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Simpan gambar", default, "PNG (*.png)"
        )
        if not filename:
            return
        if not filename.lower().endswith(".png"):
            filename += ".png"
        if self.graph_view.grab().save(filename):
            self.statusBar().showMessage(f"Gambar disimpan: {filename}", 5000)
        else:
            self.statusBar().showMessage("Gagal menyimpan gambar.", 5000)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Visualisasi Qt untuk simulasi jalur aman.")
    parser.add_argument(
        "scenario",
        nargs="?",
        default=str(DEFAULT_YAML_SCENARIO),
        help="Path file YAML skenario (default: case_01_kobra_banjir.yaml).",
    )
    args = parser.parse_args(argv)

    app = QApplication(sys.argv[:1])
    window = MainWindow(Path(args.scenario))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
