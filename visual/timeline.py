"""Horizontal, clickable timeline of simulation states."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from visual.snapshots import Snapshot

EVENT_META = {
    "INITIAL": ("Keadaan Awal", "#546e7a", "#eceff1"),
    "BLOCK_NODE": ("Blokir Node", "#c62828", "#ffebee"),
    "UNBLOCK_NODE": ("Buka Node", "#2e7d32", "#e8f5e9"),
    "BLOCK_EDGE": ("Blokir Ruas", "#c62828", "#ffebee"),
    "UNBLOCK_EDGE": ("Buka Ruas", "#2e7d32", "#e8f5e9"),
    "DYNAMIC_EDGE_WEIGHT": ("Ubah Bobot", "#b26a00", "#fff3e0"),
}


class StepCard(QFrame):
    clicked = Signal(int)

    def __init__(self, snapshot: Snapshot, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StepCard")
        self.snapshot = snapshot
        self.setFixedSize(138, 80)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QFrame#StepCard { background:#ffffff; border:1px solid #e2e8f0;"
            " border-radius:10px; }"
            "QFrame#StepCard[selected=\"true\"] { background:#eef2ff;"
            " border:2px solid #4f46e5; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        prefix = "AWAL" if snapshot.event_type == "INITIAL" else f"STEP {snapshot.step}"
        top = QLabel(prefix)
        top.setStyleSheet("color:#90a4ae; font-size:9px; font-weight:600; letter-spacing:1px;")
        layout.addWidget(top)

        title, fg, _ = EVENT_META.get(
            snapshot.event_type, (snapshot.event_type, "#455a64", "#eceff1")
        )
        self.title = QLabel(title)
        self.title.setStyleSheet(f"color:{fg}; font-size:12px; font-weight:600;")
        layout.addWidget(self.title)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(4)
        if snapshot.entity_id:
            entity = QLabel(snapshot.entity_id)
            entity.setStyleSheet(
                f"color:{fg}; background:{_}; border-radius:4px;"
                " padding:1px 4px; font-size:9px; font-weight:600;"
            )
            bottom.addWidget(entity)
        status = QLabel("AMAN" if snapshot.path else "PUTUS")
        status_color = "#2e7d32" if snapshot.path else "#c62828"
        status.setStyleSheet(
            f"color:{status_color}; font-size:9px; font-weight:700;"
        )
        bottom.addWidget(status)
        bottom.addStretch(1)
        cost = QLabel("inf" if snapshot.cost == float("inf") else f"{snapshot.cost:.1f} mnt")
        cost.setStyleSheet("color:#78909c; font-size:9px;")
        bottom.addWidget(cost)
        layout.addLayout(bottom)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.snapshot.index)
        super().mousePressEvent(event)


class StepTimeline(QScrollArea):
    step_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFixedHeight(108)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { background: transparent; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QHBoxLayout(self._container)
        self._layout.setContentsMargins(2, 6, 2, 6)
        self._layout.setSpacing(7)
        self._layout.addStretch(1)
        self.setWidget(self._container)
        self._cards: List[StepCard] = []

    def set_snapshots(self, snapshots: List[Snapshot]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._cards = []
        for snapshot in snapshots:
            card = StepCard(snapshot)
            card.clicked.connect(self.step_selected.emit)
            self._layout.addWidget(card)
            self._cards.append(card)
        self._layout.addStretch(1)

    def set_current(self, index: int) -> None:
        if not self._cards:
            return
        index = max(0, min(index, len(self._cards) - 1))
        for i, card in enumerate(self._cards):
            card.set_selected(i == index)
        self.ensureWidgetVisible(self._cards[index], 60, 0)
