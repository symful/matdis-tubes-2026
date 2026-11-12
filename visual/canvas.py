"""Graph canvas: polished scene rendering plus a zoomable/pannable view."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from visual.snapshots import ScenarioView, Snapshot

BG = QColor("#f6f8fb")

ROAD_CASING = QColor("#e4eaf1")
ROAD_CORE = QColor("#bfc9d4")
FLOOD_CASING = QColor("#fde3c2")
FLOOD_CORE = QColor("#e08a2e")
BLOCK_CASING = QColor("#f9d2d2")
BLOCK_CORE = QColor("#d64545")
PATH_CASING = QColor("#c3eccb")
PATH_CORE = QColor("#2e7d32")
TARGET = QColor("#4f46e5")

NODE_FILL = QColor("#ffffff")
NODE_BORDER = QColor("#607d8b")
START_FILL = QColor("#dcf3df")
START_BORDER = QColor("#2e7d32")
GOAL_FILL = QColor("#e8e0f5")
GOAL_BORDER = QColor("#6a4c93")
BLOCKED_FILL = QColor("#ffdcdc")
BLOCKED_BORDER = QColor("#c62828")

WHITE = QColor("#ffffff")


class NodeItem(QGraphicsEllipseItem):
    """Node circle that reports clicks (used for the status-bar label)."""

    def __init__(self, rect: QRectF, node: Dict, on_click: Optional[Callable]):
        super().__init__(rect)
        self._node = node
        self._on_click = on_click
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if self._on_click is not None:
            self._on_click(self._node)
        super().mousePressEvent(event)


class GraphView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, parent: Optional[QWidget] = None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.TextAntialiasing
            | QPainter.SmoothPixmapTransform
        )
        self.setBackgroundBrush(QBrush(BG))
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self._user_zoomed = False
        self.legend_widget: Optional[QWidget] = None
        self.compass_widget: Optional[QWidget] = None
        self.scale_widget: Optional[QWidget] = None

    def place_overlays(self) -> None:
        if self.legend_widget is not None:
            self.legend_widget.move(
                14, max(14, self.height() - self.legend_widget.height() - 14)
            )
        if self.compass_widget is not None:
            self.compass_widget.move(
                self.width() - self.compass_widget.width() - 16, 16
            )
        if self.scale_widget is not None:
            self.scale_widget.move(
                self.width() - self.scale_widget.width() - 16,
                self.height() - self.scale_widget.height() - 16,
            )
            self.scale_widget.update()

    def fit_scene(self) -> None:
        rect = self.scene().sceneRect()
        if not rect.isEmpty():
            self.fitInView(rect, Qt.KeepAspectRatio)
            self._user_zoomed = False
            if self.scale_widget is not None:
                self.scale_widget.update()

    def wheelEvent(self, event) -> None:
        if self.scene().sceneRect().isEmpty():
            return
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = self.transform().m11()
        if 0.12 <= current * factor <= 8:
            self.scale(factor, factor)
            self._user_zoomed = True
            if self.scale_widget is not None:
                self.scale_widget.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._user_zoomed:
            self.fit_scene()
        self.place_overlays()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._user_zoomed:
            self.fit_scene()
        self.place_overlays()

    def mouseDoubleClickEvent(self, event) -> None:
        self.fit_scene()
        super().mouseDoubleClickEvent(event)


class LegendOverlay(QFrame):
    """Floating legend pinned to the bottom-left of the canvas."""

    ITEMS = [
        (PATH_CORE, "Rute aman"),
        (BLOCK_CORE, "Ruas terblokir"),
        (FLOOD_CORE, "Ruas tergenang"),
        (BLOCKED_FILL, "Node terblokir"),
        (START_BORDER, "Titik A"),
        (GOAL_BORDER, "Titik B"),
        (TARGET, "Target event"),
        (QColor("#c9d5e0"), "Jalan sekitar"),
    ]

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Legend")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet(
            "#Legend { background: rgba(255,255,255,0.94);"
            " border: 1px solid #e2e8f0; border-radius: 10px; }"
            " QLabel { color: #37474f; font-size: 11px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        title = QLabel("Legenda")
        title.setStyleSheet("font-weight:600; color:#263238; font-size:11px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        self._network_widgets = []
        for index, (color, text) in enumerate(self.ITEMS):
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(
                f"background:{color.name()}; border-radius:5px;"
                f" border:1px solid {color.darker(115).name()};"
            )
            label = QLabel(text)
            grid.addWidget(dot, index // 2, (index % 2) * 2)
            grid.addWidget(label, index // 2, (index % 2) * 2 + 1)
            if text == "Jalan sekitar":
                self._network_widgets = [dot, label]
        layout.addLayout(grid)
        self.adjustSize()

    def set_network_visible(self, visible: bool) -> None:
        for widget in self._network_widgets:
            widget.setVisible(visible)
        self.adjustSize()

    def place(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.move(14, max(14, parent.height() - self.height() - 14))


class CompassOverlay(QWidget):
    """Small north indicator pinned to the top-right of the canvas."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFixedSize(46, 46)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.setPen(QPen(QColor("#dbe3ec"), 1))
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))

        cx = self.width() / 2
        cy = self.height() / 2 - 3
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor("#d64545")))
        painter.drawPolygon(
            QPolygonF([
                QPointF(cx, cy - 11),
                QPointF(cx - 4.5, cy + 3),
                QPointF(cx + 4.5, cy + 3),
            ])
        )
        painter.setPen(QColor("#455a64"))
        font = QFont("Segoe UI", 7)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, cy + 5, self.width(), 14), Qt.AlignCenter, "N")


class ScaleBarOverlay(QWidget):
    """Dynamic scale bar in metres, recomputed from the current zoom."""

    CANDIDATES = (10, 20, 50, 100, 200, 500, 1000, 2000, 5000)

    def __init__(self, view: GraphView):
        super().__init__(view)
        self._view = view
        self.setFixedSize(172, 40)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event) -> None:
        scale = self._view.transform().m11() or 1.0
        chosen = None
        for meters in self.CANDIDATES:
            pixels = meters * scale
            if 44 <= pixels <= 132:
                chosen = (meters, pixels)
                break
        if chosen is None:
            meters = min(self.CANDIDATES, key=lambda value: abs(value * scale - 88))
            chosen = (meters, meters * scale)
        meters, pixels = chosen

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)

        x0 = 14
        y = self.height() * 0.64
        painter.setPen(QPen(QColor("#455a64"), 2))
        painter.drawLine(QPointF(x0, y), QPointF(x0 + pixels, y))
        painter.drawLine(QPointF(x0, y - 4), QPointF(x0, y + 4))
        painter.drawLine(QPointF(x0 + pixels, y - 4), QPointF(x0 + pixels, y + 4))

        painter.setPen(QColor("#455a64"))
        font = QFont("Segoe UI", 7)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(x0, 3, pixels, 14), Qt.AlignCenter, f"{meters} m"
        )


class GraphRenderer:
    """Paints a :class:`ScenarioView` state into a QGraphicsScene."""

    def __init__(self, scene: QGraphicsScene, on_node_click: Optional[Callable] = None):
        self.scene = scene
        self.on_node_click = on_node_click
        self.show_network = True

    # ------------------------------------------------------------------ public
    def render(self, data: ScenarioView, snapshot: Snapshot) -> None:
        self.scene.clear()

        if self.show_network and data.network_edges:
            self._draw_network(data.network_edges)

        points = {
            node["id"]: QPointF(float(node["pos"][0]), -float(node["pos"][1]))
            for node in data.nodes
        }
        span = max(
            max(point.x() for point in points.values())
            - min(point.x() for point in points.values()),
            max(point.y() for point in points.values())
            - min(point.y() for point in points.values()),
            1e-9,
        )
        if span < 100 and not data.network_edges:
            factor = 600.0 / span
            points = {
                node_id: QPointF(point.x() * factor, point.y() * factor)
                for node_id, point in points.items()
            }
        radius = self._node_radius(points, self._min_edge_length(data, points))
        self.scene.setSceneRect(self._scene_rect(points, radius))

        blocked_nodes = set(snapshot.blocked_nodes)
        blocked_edges = {tuple(edge) for edge in snapshot.blocked_edges}
        flooded_edges = {
            edge
            for window in data.flood_windows
            if window["from_step"] <= snapshot.step <= window["to_step"]
            for edge in window["edges"]
        }
        path_edges = list(zip(snapshot.path, snapshot.path[1:]))
        path_keys = {tuple(sorted(edge)) for edge in path_edges}
        target_edge = (
            tuple(sorted(snapshot.target_edge)) if snapshot.target_edge else None
        )
        edge_by_key = {tuple(sorted((e["from"], e["to"]))): e for e in data.edges}

        for edge in data.edges:
            key = tuple(sorted((edge["from"], edge["to"])))
            if key in path_keys:
                continue
            self._draw_edge(
                edge,
                points[edge["from"]],
                points[edge["to"]],
                snapshot,
                radius,
                flooded=key in flooded_edges,
                blocked=key in blocked_edges,
                target=key == target_edge,
                path_edge=False,
            )

        for u, v in path_edges:
            key = tuple(sorted((u, v)))
            edge = edge_by_key.get(key)
            if edge is None or u not in points or v not in points:
                continue
            self._draw_edge(
                edge,
                points[u],
                points[v],
                snapshot,
                radius,
                flooded=key in flooded_edges,
                blocked=False,
                target=key == target_edge,
                path_edge=True,
            )

        for node in data.nodes:
            node_id = node["id"]
            self._draw_node(
                node,
                points[node_id],
                radius,
                data,
                snapshot,
                blocked=node_id in blocked_nodes,
                on_path=node_id in set(snapshot.path),
                target=node_id == snapshot.target_node,
            )

        self._node_labels(data, points, radius)

    def _draw_network(self, edges: List[Dict]) -> None:
        """One batched path for every surrounding OSM road, behind the case."""
        path = QPainterPath()
        for segment in edges:
            path.moveTo(segment["x1"], -segment["y1"])
            path.lineTo(segment["x2"], -segment["y2"])
        pen = QPen(QColor("#dbe4ed"), 1.3)
        pen.setCapStyle(Qt.RoundCap)
        item = QGraphicsPathItem(path)
        item.setPen(pen)
        item.setZValue(-10)
        self.scene.addItem(item)

    # ------------------------------------------------------------------ edges
    def _draw_edge(
        self,
        edge: Dict,
        start: QPointF,
        end: QPointF,
        snapshot: Snapshot,
        radius: float,
        flooded: bool,
        blocked: bool,
        target: bool,
        path_edge: bool,
    ) -> None:
        u, v = edge["from"], edge["to"]
        weight = snapshot.weights.get(
            (u, v), snapshot.weights.get((v, u), edge.get("weight", 0.0))
        )
        length = math.hypot(end.x() - start.x(), end.y() - start.y())

        if target:
            self._line(
                start, end, QColor(79, 70, 229, 70), radius * 1.05, z=-1, dash=(5, 4)
            )

        if path_edge:
            casing, core = PATH_CASING, PATH_CORE
        elif blocked:
            casing, core = BLOCK_CASING, BLOCK_CORE
        elif flooded:
            casing, core = FLOOD_CASING, FLOOD_CORE
        else:
            casing, core = ROAD_CASING, ROAD_CORE

        self._line(start, end, casing, radius * 0.62, z=0)
        core_item = self._line(
            start,
            end,
            core,
            radius * 0.30,
            z=1,
            dash=(6, 4) if flooded and not path_edge else None,
        )
        details = [
            edge.get("street") or "Gang tanpa nama",
            f"waktu {weight:.2f} menit",
            f"jarak {edge.get('distance_m', 0)} meter",
        ]
        if flooded:
            details.append("tergenang")
        if blocked:
            details.append("terblokir")
        core_item.setToolTip("\n".join(details))
        if blocked:
            cross_pen = QPen(BLOCK_CORE, max(2.0, radius * 0.18))
            cross_pen.setCapStyle(Qt.RoundCap)
            self._draw_cross(self._midpoint(start, end), radius * 0.55, cross_pen)
        if path_edge:
            self._draw_arrow(start, end, radius)

        self._street_label(start, end, edge.get("street", ""), radius)

        show_label = (
            blocked
            or flooded
            or (path_edge and length >= 42)
            or length >= 250
        )
        if show_label:
            self._edge_label(start, end, weight, flooded, blocked, path_edge, radius)

        if target and snapshot.entity_id:
            anchor = self._lerp(start, end, 0.32)
            self._pill(anchor, snapshot.entity_id, radius * 0.52, TARGET,
                       QColor("#e8e7ff"), TARGET, z=9)

    def _line(
        self,
        start: QPointF,
        end: QPointF,
        color: QColor,
        width: float,
        z: float = 0,
        dash: Optional[Tuple[int, int]] = None,
    ) -> QGraphicsLineItem:
        pen = QPen(color, width)
        pen.setCapStyle(Qt.RoundCap)
        if dash:
            pen.setDashPattern(list(dash))
        item = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        item.setPen(pen)
        item.setZValue(z)
        self.scene.addItem(item)
        return item

    def _draw_arrow(self, start: QPointF, end: QPointF, radius: float) -> None:
        mid = self._lerp(start, end, 0.58)
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        size = radius * 0.62
        tip = QPointF(mid.x() + ux * size, mid.y() + uy * size)
        left = QPointF(mid.x() - ux * size * 0.2 + nx * size * 0.62,
                       mid.y() - uy * size * 0.2 + ny * size * 0.62)
        right = QPointF(mid.x() - ux * size * 0.2 - nx * size * 0.62,
                        mid.y() - uy * size * 0.2 - ny * size * 0.62)
        item = QGraphicsPolygonItem(QPolygonF([tip, left, right]))
        item.setBrush(QBrush(PATH_CORE))
        item.setPen(QPen(PATH_CORE, 0.5))
        item.setZValue(6)
        self.scene.addItem(item)

    def _edge_label(
        self,
        start: QPointF,
        end: QPointF,
        weight: float,
        flooded: bool,
        blocked: bool,
        path_edge: bool,
        radius: float,
    ) -> None:
        mid = self._midpoint(start, end)
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = math.hypot(dx, dy) or 1.0
        anchor = QPointF(mid.x() - dy / length * radius * 0.9,
                         mid.y() + dx / length * radius * 0.9)
        if blocked:
            fg, bg, border = QColor("#b71c1c"), QColor("#ffecec"), QColor("#e29a9a")
        elif path_edge:
            fg, bg, border = QColor("#1b5e20"), QColor("#e8f5e9"), QColor("#9ccc9f")
        elif flooded:
            fg, bg, border = QColor("#a35a00"), QColor("#fff3e0"), QColor("#f0b26b")
        else:
            fg, bg, border = QColor("#546e7a"), QColor("#ffffff"), QColor("#dde5ec")
        self._pill(anchor, f"{weight:.2f}", radius * 0.5, fg, bg, border, z=8)

    def _street_label(
        self, start: QPointF, end: QPointF, street: str, radius: float
    ) -> None:
        """Paint the street name rotated along its road, like a printed map."""
        if not street or "tanpa nama" in street.lower():
            return
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = math.hypot(dx, dy)
        if length < 60:
            return
        angle = math.degrees(math.atan2(dy, dx))
        if angle > 90:
            angle -= 180
        elif angle < -90:
            angle += 180
        radians = math.radians(angle)
        nx, ny = -math.sin(radians), math.cos(radians)
        anchor = QPointF(
            start.x() + dx * 0.34 - nx * radius * 1.2,
            start.y() + dy * 0.34 - ny * radius * 1.2,
        )
        item = QGraphicsSimpleTextItem(street)
        font = QFont("Segoe UI", max(6, int(round(radius * 0.45))))
        item.setFont(font)
        item.setBrush(QBrush(QColor("#7b8a97")))
        rect = item.boundingRect()
        item.setTransformOriginPoint(rect.center())
        item.setPos(anchor.x() - rect.width() / 2, anchor.y() - rect.height() / 2)
        item.setRotation(angle)
        item.setZValue(6)
        self.scene.addItem(item)

    def _pill_size(self, text: str, font_size: float) -> Tuple[float, float]:
        font = QFont("Segoe UI", max(6, int(round(font_size))))
        font.setBold(True)
        rect = QFontMetricsF(font).boundingRect(text)
        pad_x, pad_y = max(2.0, font_size * 0.45), max(1.5, font_size * 0.3)
        return rect.width() + pad_x * 2, rect.height() + pad_y * 2

    @staticmethod
    def _short_name(label: str) -> str:
        first = label.split(",")[0].strip()
        first = first.replace("Simpang ", "")
        parts = [part.strip() for part in first.split(" - ") if part.strip()]
        text = " / ".join(parts)
        if len(text) > 26:
            text = text[:25] + "\u2026"
        return text

    def _node_labels(
        self, data: ScenarioView, points: Dict[int, QPointF], radius: float
    ) -> None:
        """Place place names around nodes, skipping labels that would collide."""
        scene_rect = self.scene.sceneRect()
        occupied = [
            QRectF(point.x() - radius * 1.25, point.y() - radius * 1.25,
                   radius * 2.5, radius * 2.5)
            for point in points.values()
        ]
        font_size = max(6.0, radius * 0.46)
        skip = {data.plan.get("start_node"), data.plan.get("goal_node")}

        for node in data.nodes:
            node_id = node["id"]
            if node_id in skip:
                continue
            text = self._short_name(node.get("label", ""))
            if not text:
                continue
            width, height = self._pill_size(text, font_size)
            x, y = points[node_id].x(), points[node_id].y()
            candidates = [
                QPointF(x, y + radius * 1.45 + height / 2),
                QPointF(x, y - radius * 1.45 - height / 2),
                QPointF(x + radius * 1.45 + width / 2, y),
                QPointF(x - radius * 1.45 - width / 2, y),
            ]
            for anchor in candidates:
                rect = QRectF(
                    anchor.x() - width / 2, anchor.y() - height / 2, width, height
                )
                if not scene_rect.contains(rect):
                    continue
                if any(rect.adjusted(-2, -2, 2, 2).intersects(area) for area in occupied):
                    continue
                self._pill(
                    anchor, text, font_size, QColor("#455a64"),
                    QColor(255, 255, 255, 235), QColor("#dbe3ec"), z=13,
                )
                occupied.append(rect)
                break

    # ------------------------------------------------------------------ nodes
    def _draw_node(
        self,
        node: Dict,
        point: QPointF,
        radius: float,
        data: ScenarioView,
        snapshot: Snapshot,
        blocked: bool,
        on_path: bool,
        target: bool,
    ) -> None:
        node_id = node["id"]
        start_id = data.plan.get("start_node")
        goal_id = data.plan.get("goal_node")

        if blocked:
            fill, border = BLOCKED_FILL, BLOCKED_BORDER
        elif node_id == start_id:
            fill, border = START_FILL, START_BORDER
        elif node_id == goal_id:
            fill, border = GOAL_FILL, GOAL_BORDER
        else:
            fill, border = NODE_FILL, NODE_BORDER

        halo = QGraphicsEllipseItem(
            point.x() - radius * 1.18, point.y() - radius * 1.18,
            radius * 2.36, radius * 2.36,
        )
        halo.setBrush(QBrush(WHITE))
        halo.setPen(QPen(Qt.NoPen))
        halo.setZValue(9)
        self.scene.addItem(halo)

        circle = NodeItem(
            QRectF(point.x() - radius, point.y() - radius, radius * 2, radius * 2),
            node,
            self.on_node_click,
        )
        circle.setBrush(QBrush(fill))
        width = radius * 0.18 if on_path else radius * 0.11
        circle.setPen(QPen(border, width))
        circle.setZValue(10)
        circle.setToolTip(
            self._node_tooltip(node)
        )
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(radius * 0.9)
        shadow.setOffset(0, radius * 0.16)
        shadow.setColor(QColor(15, 23, 42, 55))
        circle.setGraphicsEffect(shadow)
        self.scene.addItem(circle)

        if on_path:
            ring = QGraphicsEllipseItem(
                point.x() - radius * 1.16, point.y() - radius * 1.16,
                radius * 2.32, radius * 2.32,
            )
            ring_pen = QPen(PATH_CORE, max(1.2, radius * 0.09))
            ring_pen.setStyle(Qt.SolidLine)
            ring.setPen(ring_pen)
            ring.setBrush(QBrush(Qt.NoBrush))
            ring.setZValue(9.5)
            self.scene.addItem(ring)

        if target:
            target_ring = QGraphicsEllipseItem(
                point.x() - radius * 1.42, point.y() - radius * 1.42,
                radius * 2.84, radius * 2.84,
            )
            pen = QPen(TARGET, max(1.5, radius * 0.11))
            pen.setStyle(Qt.DashLine)
            target_ring.setPen(pen)
            target_ring.setBrush(QBrush(Qt.NoBrush))
            target_ring.setZValue(10.5)
            self.scene.addItem(target_ring)

        self._text(point, str(node_id), radius * 0.72, QColor("#1f2933"), bold=True, z=12)

        if blocked:
            self._draw_cross(point, radius * 0.58, QPen(BLOCKED_BORDER, max(2.0, radius * 0.2)))
            entity = snapshot.blocker_map.get(f"node:{node_id}")
            if entity:
                self._pill(
                    QPointF(point.x(), point.y() - radius * 1.95),
                    entity, radius * 0.5, QColor("#b71c1c"),
                    QColor("#ffecec"), QColor("#e29a9a"), z=13,
                )
        elif node_id == start_id:
            self._pill(
                QPointF(point.x() - radius * 1.15, point.y() + radius * 1.15),
                "A", radius * 0.62, START_BORDER,
                QColor("#e8f5e9"), QColor("#a5d6a7"), z=13,
            )
        elif node_id == goal_id:
            self._pill(
                QPointF(point.x() + radius * 1.15, point.y() - radius * 1.15),
                "B", radius * 0.62, GOAL_BORDER,
                QColor("#f3e8ff"), QColor("#c4b5fd"), z=13,
            )

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _min_edge_length(data: ScenarioView, points: Dict[int, QPointF]) -> float:
        lengths = []
        for edge in data.edges:
            a, b = points.get(edge["from"]), points.get(edge["to"])
            if a is None or b is None:
                continue
            length = math.hypot(a.x() - b.x(), a.y() - b.y())
            if length > 0:
                lengths.append(length)
        return min(lengths) if lengths else 1.0

    @staticmethod
    def _node_tooltip(node: Dict) -> str:
        lines = [f"Node {node['id']}", node.get("label", "")]
        if node.get("lat") is not None and node.get("lon") is not None:
            lines.append(f"Koordinat: {node['lat']}, {node['lon']}")
        pos = node.get("pos")
        if pos:
            lines.append(f"Posisi: {float(pos[0]):.1f} m, {float(pos[1]):.1f} m")
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _node_radius(points: Dict[int, QPointF], min_edge: float) -> float:
        xs = [p.x() for p in points.values()]
        ys = [p.y() for p in points.values()]
        span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
        return max(8.0, min(20.0, min(span * 0.02, min_edge * 0.32)))

    @staticmethod
    def _scene_rect(points: Dict[int, QPointF], radius: float) -> QRectF:
        xs = [p.x() for p in points.values()]
        ys = [p.y() for p in points.values()]
        margin = radius * 6
        return QRectF(
            min(xs) - margin,
            min(ys) - margin,
            (max(xs) - min(xs)) + margin * 2,
            (max(ys) - min(ys)) + margin * 2,
        )

    def _text(
        self,
        point: QPointF,
        text: str,
        size: float,
        color: QColor,
        bold: bool = False,
        z: float = 20,
    ) -> None:
        item = QGraphicsSimpleTextItem(text)
        font = QFont("Segoe UI", max(6, int(round(size))))
        font.setBold(bold)
        item.setFont(font)
        item.setBrush(QBrush(color))
        rect = item.boundingRect()
        item.setPos(point.x() - rect.width() / 2, point.y() - rect.height() / 2)
        item.setZValue(z)
        self.scene.addItem(item)

    def _pill(
        self,
        anchor: QPointF,
        text: str,
        font_size: float,
        fg: QColor,
        bg: QColor,
        border: Optional[QColor] = None,
        z: float = 30,
    ) -> None:
        font = QFont("Segoe UI", max(6, int(round(font_size))))
        font.setBold(True)
        metrics = QFontMetricsF(font)
        text_rect = metrics.boundingRect(text)
        pad_x, pad_y = max(2.0, font_size * 0.45), max(1.5, font_size * 0.3)
        width = text_rect.width() + pad_x * 2
        height = text_rect.height() + pad_y * 2

        path = QPainterPath()
        radius = height * 0.45
        path.addRoundedRect(
            QRectF(anchor.x() - width / 2, anchor.y() - height / 2, width, height),
            radius,
            radius,
        )
        chip = QGraphicsPathItem(path)
        chip.setBrush(QBrush(bg))
        chip.setPen(QPen(border, max(0.8, font_size * 0.09)) if border else QPen(Qt.NoPen))
        chip.setZValue(z)
        self.scene.addItem(chip)

        label = QGraphicsSimpleTextItem(text)
        label.setFont(font)
        label.setBrush(QBrush(fg))
        label.setPos(
            anchor.x() - text_rect.width() / 2,
            anchor.y() - text_rect.height() / 2,
        )
        label.setZValue(z + 0.5)
        self.scene.addItem(label)

    def _draw_cross(self, center: QPointF, size: float, pen: QPen) -> None:
        pen.setCapStyle(Qt.RoundCap)
        for sx, sy in ((1, 1), (1, -1)):
            item = QGraphicsLineItem(
                center.x() - size * sx, center.y() - size * sy,
                center.x() + size * sx, center.y() + size * sy,
            )
            item.setPen(pen)
            item.setZValue(11)
            self.scene.addItem(item)

    @staticmethod
    def _midpoint(a: QPointF, b: QPointF) -> QPointF:
        return QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)

    @staticmethod
    def _lerp(a: QPointF, b: QPointF, t: float) -> QPointF:
        return QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t)
