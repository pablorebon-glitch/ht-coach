from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.ui.design_system import spacing


class BasePage(QWidget):
    def __init__(
        self,
        title,
        subtitle,
        parent=None
    ):
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.page_header = QFrame()
        self.page_header.setObjectName("pageHeader")
        self.page_header_layout = QVBoxLayout(self.page_header)
        header_layout = self.page_header_layout
        header_layout.setContentsMargins(spacing.XL, 18, spacing.XL, spacing.LG)
        header_layout.setSpacing(spacing.XS)

        self.page_title_row = QHBoxLayout()
        self.page_title_row.setContentsMargins(0, 0, 0, 0)
        self.page_title_row.setSpacing(spacing.SM)

        self.page_title_label = QLabel(title)
        self.page_title_label.setObjectName("pageTitle")

        self.page_source_label = QLabel("")
        self.page_source_label.setObjectName("statusBadge")
        self.page_source_label.setProperty("semanticStatus", "neutral")
        self.page_source_label.setVisible(False)

        self.page_subtitle_label = QLabel(subtitle)
        self.page_subtitle_label.setObjectName("pageSubtitle")
        self.page_subtitle_label.setWordWrap(True)

        self.page_title_row.addWidget(self.page_title_label)
        self.page_title_row.addStretch(1)
        self.page_title_row.addWidget(self.page_source_label)
        header_layout.addLayout(self.page_title_row)
        header_layout.addWidget(self.page_subtitle_label)
        layout.addWidget(self.page_header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(spacing.XL, spacing.XL, spacing.XL, spacing.XL)
        body_layout.setSpacing(spacing.LG)
        body_layout.setAlignment(Qt.AlignTop)

        self.body_layout = body_layout
        layout.addWidget(body, 1)

    def set_page_text(self, title, subtitle):
        self.page_title_label.setText(title)
        self.page_subtitle_label.setText(subtitle)

    def set_source_indicator(self, text="", status="neutral"):
        self.page_source_label.setText(text)
        self.page_source_label.setProperty("semanticStatus", status)
        self.page_source_label.setVisible(bool(text))
        self.page_source_label.style().unpolish(self.page_source_label)
        self.page_source_label.style().polish(self.page_source_label)

    def set_compact_header(self, compact):
        self.page_subtitle_label.setVisible(not compact)
        if compact:
            self.page_header_layout.setContentsMargins(spacing.LG, 7, spacing.LG, 7)
            self.page_header_layout.setSpacing(0)
        else:
            self.page_header_layout.setContentsMargins(
                spacing.XL,
                18,
                spacing.XL,
                spacing.LG,
            )
            self.page_header_layout.setSpacing(spacing.XS)
