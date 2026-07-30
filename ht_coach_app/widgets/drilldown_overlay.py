from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.core.localization import t


class DrillDownOverlay(QWidget):
    """A centered modal drill-down over a translucent full-parent
    overlay -- the reusable interaction pattern behind every Club
    Advisor card (Part 8). Left side: a clickable list of rows. Right
    side: the detail for whichever row is selected (first row selected
    by default). Closes via the Close button, ESC, or a click outside
    the centered panel."""

    closed = Signal()

    def __init__(self, title, rows, parent=None):
        """`rows` is a list of (row_label, detail_text) pairs."""
        super().__init__(parent)
        self._rows = rows

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 140))
        self.setPalette(palette)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        center_row = QHBoxLayout()
        center_row.addStretch(1)

        self.panel = QFrame(self)
        self.panel.setObjectName("drillDownPanel")
        self.panel.setAutoFillBackground(True)
        self.panel.setMinimumSize(560, 360)
        self.panel.setMaximumSize(820, 560)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(16, 14, 16, 14)
        panel_layout.setSpacing(10)

        header_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        self.close_button = QPushButton(t("club_advisor.drilldown.close"))
        self.close_button.clicked.connect(self.close_overlay)
        header_row.addWidget(title_label, 1)
        header_row.addWidget(self.close_button)
        panel_layout.addLayout(header_row)

        body_row = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(220)
        self.list_widget.currentRowChanged.connect(self._show_detail_for_row)
        for label, _detail in rows:
            QListWidgetItem(label, self.list_widget)

        detail_panel = QFrame()
        detail_panel.setObjectName("drillDownDetailPanel")
        detail_layout = QGridLayout(detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setHorizontalSpacing(10)
        detail_layout.setVerticalSpacing(8)

        self.explanation_label = QLabel("")
        self.players_label = QLabel("")
        self.reason_label = QLabel("")
        self.impact_label = QLabel("")
        self.review_label = QLabel("")
        self.detail_label = QLabel("")
        for label in (
            self.explanation_label,
            self.players_label,
            self.reason_label,
            self.impact_label,
            self.review_label,
            self.detail_label,
        ):
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        for row, heading in enumerate(
            (
                t("club_advisor.panel.explanation"),
                t("club_advisor.panel.players_involved"),
                t("club_advisor.panel.reason"),
                t("club_advisor.panel.impact"),
                t("club_advisor.panel.review"),
            )
        ):
            heading_label = QLabel(heading)
            heading_label.setObjectName("drillDownFieldHeading")
            heading_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            detail_layout.addWidget(heading_label, row, 0)

        detail_layout.addWidget(self.explanation_label, 0, 1)
        detail_layout.addWidget(self.players_label, 1, 1)
        detail_layout.addWidget(self.reason_label, 2, 1)
        detail_layout.addWidget(self.impact_label, 3, 1)
        detail_layout.addWidget(self.review_label, 4, 1)
        detail_layout.addWidget(self.detail_label, 5, 0, 1, 2)
        self.detail_label.setWordWrap(True)

        body_row.addWidget(self.list_widget)
        body_row.addWidget(detail_panel, 1)
        panel_layout.addLayout(body_row, 1)

        center_row.addWidget(self.panel)
        center_row.addStretch(1)
        outer.addLayout(center_row)
        outer.addStretch(1)

        if rows:
            self.list_widget.setCurrentRow(0)
        self.panel.raise_()

    def _show_detail_for_row(self, index):
        if 0 <= index < len(self._rows):
            detail = self._rows[index][1]
            fields = self._detail_fields(detail)
            self.explanation_label.setText(fields.get("explanation", self._rows[index][0]))
            self.players_label.setText(fields.get("players involved", "-"))
            self.reason_label.setText(fields.get("reason", "-"))
            self.impact_label.setText(fields.get("impact", "-"))
            self.review_label.setText(fields.get("review", "-"))
            self.detail_label.setText(fields.get("other", ""))

    @staticmethod
    def _detail_fields(detail):
        key_map = {
            "explanation": {
                "explanation",
                t("club_advisor.panel.explanation").strip().lower(),
            },
            "players involved": {
                "players involved",
                "affected players",
                t("club_advisor.panel.players_involved").strip().lower(),
                t("club_advisor.panel.affected_players").strip().lower(),
            },
            "reason": {
                "reason",
                t("club_advisor.panel.reason").strip().lower(),
            },
            "impact": {
                "impact",
                t("club_advisor.panel.impact").strip().lower(),
            },
            "review": {
                "review",
                t("club_advisor.panel.review").strip().lower(),
            },
        }
        fields = {}
        other = []
        for line in str(detail or "").splitlines():
            if ":" not in line:
                other.append(line)
                continue
            key, value = line.split(":", 1)
            normalized = key.strip().lower()
            canonical = next(
                (name for name, aliases in key_map.items() if normalized in aliases),
                "",
            )
            if canonical:
                fields[canonical] = value.strip()
            else:
                other.append(line)
        fields["other"] = "\n".join(other).strip()
        return fields

    def close_overlay(self):
        self.setParent(None)
        self.closed.emit()
        self.deleteLater()

    def mousePressEvent(self, event):
        if not self.panel.geometry().contains(event.pos()):
            self.close_overlay()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close_overlay()
            return
        super().keyPressEvent(event)

    @staticmethod
    def show_over(parent, title, rows):
        overlay = DrillDownOverlay(title, rows, parent=parent)
        overlay.setGeometry(parent.rect())
        overlay.show()
        overlay.setFocus()
        return overlay
