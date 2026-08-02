from PySide6.QtCore import QObject, Signal


class AppEvents(QObject):
    opponents_changed = Signal(str, str, str)
    roster_changed = Signal(str, int)
    language_changed = Signal(str)
    advisor_verbosity_changed = Signal(str)
    official_ratings_changed = Signal(str)
    weekly_plan_saved = Signal()
    open_saved_match_requested = Signal(str)
