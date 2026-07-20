from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ht_coach_app.ui.design_system.icons import STATUS_ICONS
from ht_coach_app.ui.design_system.status import normalize_status


class StatusBadge(QLabel):
    def __init__(
        self,
        status="neutral",
        label="",
        icon=None,
        compact=False,
        accessible_description="",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignCenter)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setMinimumHeight(22)
        self.set_status(
            status,
            label,
            icon=icon,
            compact=compact,
            accessible_description=accessible_description,
        )

    def set_status(
        self,
        status,
        label,
        icon=None,
        compact=False,
        accessible_description="",
    ):
        semantic_status = normalize_status(status)
        self.setProperty("semanticStatus", semantic_status)
        self.setProperty("compact", "true" if compact else "false")
        prefix = icon if icon is not None else STATUS_ICONS.get(semantic_status, "")
        text = str(label or "").strip()
        if compact:
            self.setText(text)
        else:
            self.setText(f"{prefix} {text}".strip())
        self.setToolTip(accessible_description or text)
        self.setAccessibleName(accessible_description or text)
        self.style().unpolish(self)
        self.style().polish(self)
