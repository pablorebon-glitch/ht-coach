from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class SectionHeader(QWidget):
    def __init__(
        self,
        title,
        subtitle="",
        status_widget=None,
        action_widget=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("sectionHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        text_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("sectionSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        text_layout.addWidget(self.subtitle_label)

        layout.addLayout(text_layout, 1)
        if status_widget is not None:
            layout.addWidget(status_widget)
        if action_widget is not None:
            layout.addWidget(action_widget)

    def set_text(self, title, subtitle=""):
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))
