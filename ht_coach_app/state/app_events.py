from PySide6.QtCore import QObject, Signal


class AppEvents(QObject):
    opponents_changed = Signal(str, str, str)
    roster_changed = Signal(str, int)
