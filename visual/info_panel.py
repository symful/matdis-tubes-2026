"""Side panel with status, metrics, a written explanation, and route details."""

from __future__ import annotations

from html import escape
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from visual.snapshots import ScenarioView, Snapshot


class MetricCard(QFrame):
    def __init__(self, caption: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setStyleSheet(
            "QFrame#MetricCard { background:#f4f7fb; border:1px solid #e5ebf2;"
            " border-radius:10px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(0)
        self.value = QLabel("\u2014")
        self.value.setStyleSheet("font-size:20px; font-weight:700; color:#1f2933;")
        self.caption = QLabel(caption)
        self.caption.setStyleSheet("font-size:10px; color:#78909c;")
        layout.addWidget(self.value)
        layout.addWidget(self.caption)

    def set_value(self, text: str, color: str = "#1f2933") -> None:
        self.value.setText(text)
        self.value.setStyleSheet(f"font-size:20px; font-weight:700; color:{color};")


class InfoPanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: Optional[ScenarioView] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        self.title = QLabel("\u2014")
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size:17px; font-weight:700; color:#1f2933;")
        layout.addWidget(self.title)

        self.subtitle = QLabel()
        self.subtitle.setStyleSheet("font-size:11px; color:#90a4ae;")
        layout.addWidget(self.subtitle)

        self.group = QLabel()
        self.group.setWordWrap(True)
        self.group.setStyleSheet("font-size:10px; color:#90a4ae;")
        layout.addWidget(self.group)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.banner)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self.time_card = MetricCard("Waktu (menit)")
        self.distance_card = MetricCard("Jarak (meter)")
        self.nodes_card = MetricCard("Node pada rute")
        self.blockers_card = MetricCard("Blocker aktif")
        grid.addWidget(self.time_card, 0, 0)
        grid.addWidget(self.distance_card, 0, 1)
        grid.addWidget(self.nodes_card, 1, 0)
        grid.addWidget(self.blockers_card, 1, 1)
        layout.addLayout(grid)

        layout.addWidget(self._heading("Penjelasan"))
        self.event = QLabel()
        self.event.setWordWrap(True)
        self.event.setTextFormat(Qt.RichText)
        self.event.setStyleSheet(
            "background:#f4f7fb; border:1px solid #e5ebf2; border-radius:8px;"
            " padding:10px; color:#37474f; font-size:12px; line-height:150%;"
        )
        layout.addWidget(self.event)

        layout.addWidget(self._heading("Rute aman"))
        self.path = QLabel()
        self.path.setWordWrap(True)
        self.path.setTextFormat(Qt.RichText)
        self.path.setStyleSheet("font-size:12px; color:#263238;")
        layout.addWidget(self.path)

        layout.addWidget(self._heading("Ruas dilalui"))
        self.streets = QLabel()
        self.streets.setWordWrap(True)
        self.streets.setTextFormat(Qt.RichText)
        self.streets.setStyleSheet("font-size:12px; color:#455a64;")
        layout.addWidget(self.streets)

        layout.addWidget(self._heading("Blocker aktif"))
        self.blockers = QLabel()
        self.blockers.setWordWrap(True)
        self.blockers.setTextFormat(Qt.RichText)
        self.blockers.setStyleSheet("font-size:12px; color:#455a64;")
        layout.addWidget(self.blockers)

        layout.addStretch(1)

    @staticmethod
    def _heading(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setStyleSheet(
            "font-size:9px; font-weight:700; color:#90a4ae; letter-spacing:1px;"
        )
        return label

    def set_view(self, data: ScenarioView) -> None:
        self._data = data
        self.title.setText(data.metadata.get("title", data.yaml_path.stem))
        self.subtitle.setText(
            f"{data.yaml_path.name}  \u00b7  {len(data.snapshots)} keadaan"
        )
        group = data.metadata.get("group")
        if group:
            self.group.setText(f"Kelompok: {group}")
            self.group.show()
        else:
            self.group.hide()

    def set_snapshot(self, snapshot: Snapshot) -> None:
        data = self._data
        if data is None:
            return
        previous = (
            data.snapshots[snapshot.index - 1] if snapshot.index > 0 else None
        )

        if snapshot.path:
            self.banner.setText("RUTE AMAN")
            self.banner.setStyleSheet(
                "background:#e8f5e9; color:#1b5e20; border:1px solid #a5d6a7;"
                " border-radius:9px; padding:9px; font-size:13px; font-weight:700;"
            )
            self.time_card.set_value(
                "inf" if snapshot.cost == float("inf") else f"{snapshot.cost:.1f}"
            )
        else:
            self.banner.setText("TIDAK ADA RUTE AMAN")
            self.banner.setStyleSheet(
                "background:#ffebee; color:#b71c1c; border:1px solid #ef9a9a;"
                " border-radius:9px; padding:9px; font-size:13px; font-weight:700;"
            )
            self.time_card.set_value("\u2014", "#c62828")

        self.distance_card.set_value(f"{snapshot.meters:.0f}")
        self.nodes_card.set_value(str(len(snapshot.path)))
        self.blockers_card.set_value(
            str(len(snapshot.active_blockers)),
            "#c62828" if snapshot.active_blockers else "#2e7d32",
        )

        self.path.setText(self._path_html(snapshot))
        self.streets.setText(self._streets_html(snapshot))
        self.blockers.setText(self._blockers_html(snapshot))
        self.event.setText(self._explanation_html(snapshot, previous))

    # ------------------------------------------------------------ paragraphs
    def _explanation_html(
        self, snapshot: Snapshot, previous: Optional[Snapshot]
    ) -> str:
        paragraphs = [
            self._event_paragraph(snapshot, previous),
            self._route_paragraph(snapshot),
            self._blocker_paragraph(snapshot),
        ]
        caption = (
            f'<p style="margin:0 0 8px 0; color:#90a4ae; font-size:10px;">'
            f"{escape(self._clean(snapshot.label))}</p>"
        )
        body = "".join(
            f'<p style="margin:0 0 8px 0;">{escape(paragraph)}</p>'
            for paragraph in paragraphs
            if paragraph
        )
        return caption + body

    def _event_paragraph(
        self, snapshot: Snapshot, previous: Optional[Snapshot]
    ) -> str:
        data = self._data
        if data is None:
            return ""
        event_type = snapshot.event_type
        entity = data.entities.get(snapshot.entity_id or "", {})
        label = self._entity_short(entity)

        if event_type == "INITIAL":
            parts: List[str] = []
            for key in sorted(snapshot.blocker_map):
                entity_id = snapshot.blocker_map[key]
                blocker = self._entity_short(data.entities.get(entity_id, {}))
                if key.startswith("node:"):
                    node_id = int(key.split(":", 1)[1])
                    parts.append(
                        f"{blocker} menempati {self._node_phrase(node_id)} "
                        f"pada node {node_id}."
                    )
                else:
                    pair = key.split(":", 1)[1]
                    u, v = (int(value) for value in pair.split("-"))
                    parts.append(
                        f"{blocker} menutup penuh {self._street_name(u, v)} "
                        f"pada ruas {u} menuju {v}."
                    )
            for window in data.flood_windows:
                if not (window["from_step"] <= snapshot.step <= window["to_step"]):
                    continue
                if not window["edges"]:
                    continue
                u, v = sorted(window["edges"])[0]
                weight = snapshot.weights.get(
                    (u, v), snapshot.weights.get((v, u), 0.0)
                )
                flood = self._entity_short(
                    data.entities.get(window["entity_id"], {})
                )
                parts.append(
                    f"{flood} membuat waktu tempuh {self._street_name(u, v)} "
                    f"pada ruas {u} menuju {v} membengkak menjadi "
                    f"{weight:.2f} menit, tetapi ruas itu masih bisa dilewati."
                )
            if not parts:
                return "Keadaan awal tidak memuat blocker maupun genangan."
            return "Kondisi awal sudah memuat tekanan lapangan berikut. " + " ".join(
                parts
            )

        if event_type in ("BLOCK_NODE", "UNBLOCK_NODE"):
            node_id = snapshot.target_node
            title = self._node_phrase(node_id)
            group = entity.get("group_size")
            size = f" sebanyak {group} ekor" if group and group > 1 else ""
            if event_type == "BLOCK_NODE":
                return (
                    f"{label}{size} menempati {title} pada node {node_id}. "
                    f"Simpang itu tidak boleh dilalui sehingga lintasan yang "
                    f"melewatinya terputus."
                )
            return (
                f"{label}{size} sudah tidak berada di {title} pada node {node_id}. "
                f"Simpang itu kembali aman untuk dilalui."
            )

        if event_type in ("BLOCK_EDGE", "UNBLOCK_EDGE"):
            u, v = snapshot.target_edge
            street = self._street_name(u, v)
            if event_type == "BLOCK_EDGE":
                return (
                    f"{label} menutup penuh {street} pada ruas {u} menuju {v}. "
                    f"Ruas itu tidak bisa dilewati dari dua arah."
                )
            return (
                f"{label} sudah dibersihkan sehingga {street} pada ruas "
                f"{u} menuju {v} kembali terbuka dari dua arah."
            )

        if event_type == "DYNAMIC_EDGE_WEIGHT" and snapshot.target_edge:
            u, v = snapshot.target_edge
            street = self._street_name(u, v)
            new_weight = snapshot.new_weight
            old_weight = None
            if previous is not None:
                old_weight = previous.weights.get(
                    (u, v), previous.weights.get((v, u))
                )
            if old_weight is not None and new_weight is not None:
                if new_weight > old_weight:
                    return (
                        f"{label} menaikkan waktu tempuh {street} pada ruas "
                        f"{u} menuju {v} dari {old_weight:.2f} menjadi "
                        f"{new_weight:.2f} menit."
                    )
                return (
                    f"{label} sudah surut sehingga waktu tempuh {street} pada "
                    f"ruas {u} menuju {v} kembali dari {old_weight:.2f} menjadi "
                    f"{new_weight:.2f} menit."
                )
            if new_weight is not None:
                return (
                    f"Bobot {street} pada ruas {u} menuju {v} diperbarui "
                    f"menjadi {new_weight:.2f} menit."
                )

        return self._clean(snapshot.description)

    def _route_paragraph(self, snapshot: Snapshot) -> str:
        data = self._data
        if data is None:
            return ""
        start = data.plan.get("start_node")
        goal = data.plan.get("goal_node")
        if not snapshot.path:
            return (
                f"Tidak ada lintasan bebas blocker dari Titik A pada node {start} "
                f"ke Titik B pada node {goal}. Kedua titik tetap terpisah pada "
                f"keadaan ini."
            )
        chain = " \u2192 ".join(str(node) for node in snapshot.path)
        streets: List[str] = []
        for u, v in zip(snapshot.path, snapshot.path[1:]):
            street = self._street_name(u, v)
            if street not in streets:
                streets.append(street)
        street_text = ", ".join(streets)
        return (
            f"Rute aman bergerak dari node {snapshot.path[0]} sampai node "
            f"{snapshot.path[-1]} dengan urutan {chain}. Total waktu tempuh "
            f"{snapshot.cost:.2f} menit dan jarak {snapshot.meters:.0f} meter. "
            f"Ruas yang dilewati adalah {street_text}."
        )

    def _blocker_paragraph(self, snapshot: Snapshot) -> str:
        data = self._data
        if data is None or not snapshot.active_blockers:
            return (
                "Tidak ada blocker aktif. Seluruh simpang dan ruas pada peta "
                "dapat dilalui."
            )
        items = [
            f"{entity_id} yang merupakan "
            f"{self._clean(data.entity_labels.get(entity_id, entity_id))}"
            for entity_id in snapshot.active_blockers
        ]
        joined = self._join_indonesian(items)
        if snapshot.path:
            return (
                f"Blocker yang masih aktif adalah {joined}. Rute aman di atas "
                f"sudah menghindari seluruh blocker tersebut."
            )
        return (
            f"Blocker yang masih aktif adalah {joined}. Blocker itulah yang "
            f"memutus semua lintasan menuju Titik B."
        )

    @staticmethod
    def _join_indonesian(items: List[str]) -> str:
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} dan {items[1]}"
        return ", ".join(items[:-1]) + f", dan {items[-1]}"

    # ----------------------------------------------------------------- naming
    @staticmethod
    def _clean(text: object) -> str:
        return " ".join(str(text).replace(";", ".").split())

    @staticmethod
    def _entity_short(entity: dict) -> str:
        kind = {
            "snakes": "Kobra",
            "trash": "Tumpukan sampah",
            "flood": "Genangan",
        }.get(entity.get("_group"), "Blocker")
        entity_id = entity.get("id", "")
        return f"{kind} {entity_id}".strip()

    def _node_phrase(self, node_id: int) -> str:
        data = self._data
        if data is None:
            return f"Node {node_id}"
        node = data.node_by_id.get(node_id, {})
        label = str(node.get("label", f"Node {node_id}")).split(",")[0]
        label = label.replace("Simpang ", "")
        parts = [part.strip() for part in label.split(" - ") if part.strip()]
        return self._clean(" / ".join(parts))

    def _compact_node(self, node_id: int) -> str:
        data = self._data
        if data is None:
            return f"Node {node_id}"
        node = data.node_by_id.get(node_id, {})
        label = str(node.get("label", f"Node {node_id}")).split(",")[0]
        label = label.replace("Simpang ", "")
        parts = [part.strip() for part in label.split(" - ") if part.strip()]
        text = " / ".join(parts)
        if len(text) > 26:
            text = text[:25] + "\u2026"
        return self._clean(text)

    def _street_name(self, u: int, v: int) -> str:
        data = self._data
        if data is None:
            return "gang tanpa nama"
        edge = data.edge_meta.get((u, v)) or data.edge_meta.get((v, u)) or {}
        return self._clean(edge.get("street") or "gang tanpa nama")

    # ------------------------------------------------------------------ panels
    def _path_html(self, snapshot: Snapshot) -> str:
        if not snapshot.path:
            return (
                '<span style="color:#c62828;">Tidak ada lintasan bebas blocker '
                "dari Titik A ke Titik B pada keadaan ini.</span>"
            )
        chips = [
            f'<b>{node}</b> <span style="color:#78909c;">'
            f"{escape(self._compact_node(node))}</span>"
            for node in snapshot.path
        ]
        return " &rarr; ".join(chips)

    def _streets_html(self, snapshot: Snapshot) -> str:
        data = self._data
        if data is None or not snapshot.path:
            return '<span style="color:#90a4ae;">\u2014</span>'
        rows = []
        for u, v in zip(snapshot.path, snapshot.path[1:]):
            weight = snapshot.weights.get(
                (u, v), snapshot.weights.get((v, u), 0.0)
            )
            rows.append(
                f"&bull; {escape(self._street_name(u, v))} "
                f'<span style="color:#90a4ae;">(node {u} &rarr; {v}) '
                f"{weight:.2f} mnt</span>"
            )
        return "<br>".join(rows) or '<span style="color:#90a4ae;">\u2014</span>'

    def _blockers_html(self, snapshot: Snapshot) -> str:
        data = self._data
        if data is None or not snapshot.active_blockers:
            return '<span style="color:#2e7d32;">Tidak ada blocker aktif.</span>'
        rows = []
        for entity_id in snapshot.active_blockers:
            label = self._clean(data.entity_labels.get(entity_id, ""))
            rows.append(
                f'&bull; <b style="color:#c62828;">{entity_id}</b> \u2014 '
                f"{escape(label)}"
            )
        return "<br>".join(rows)
