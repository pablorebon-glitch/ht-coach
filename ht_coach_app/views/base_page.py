from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


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
        header_layout.setContentsMargins(24, 18, 24, 16)
        header_layout.setSpacing(4)

        self.page_title_label = QLabel(title)
        self.page_title_label.setObjectName("pageTitle")

        self.page_subtitle_label = QLabel(subtitle)
        self.page_subtitle_label.setObjectName("pageSubtitle")
        self.page_subtitle_label.setWordWrap(True)

        header_layout.addWidget(self.page_title_label)
        header_layout.addWidget(self.page_subtitle_label)
        layout.addWidget(self.page_header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 24, 24, 24)
        body_layout.setSpacing(16)
        body_layout.setAlignment(Qt.AlignTop)

        self.body_layout = body_layout
        layout.addWidget(body, 1)

    def set_compact_header(self, compact):
        self.page_subtitle_label.setVisible(not compact)
        if compact:
            self.page_header_layout.setContentsMargins(16, 7, 16, 7)
            self.page_header_layout.setSpacing(0)
        else:
            self.page_header_layout.setContentsMargins(24, 18, 24, 16)
            self.page_header_layout.setSpacing(4)
