from PySide6.QtWidgets import QFormLayout, QWidget

from ht_coach_app.core.localization import t
from ht_coach_app.services.opponent_service import (
    ALL_RATING_FIELDS,
    DEFAULT_RATINGS,
)
from ht_coach_app.widgets.decimal_spin_box import DecimalSpinBox


RATING_LABELS = {
    "midfield": "opponents.rating.midfield",
    "right_defense": "opponents.rating.right_defense",
    "central_defense": "opponents.rating.central_defense",
    "left_defense": "opponents.rating.left_defense",
    "right_attack": "opponents.rating.right_attack",
    "central_attack": "opponents.rating.central_attack",
    "left_attack": "opponents.rating.left_attack",
    "indirect_defense": "opponents.rating.indirect_defense",
    "indirect_attack": "opponents.rating.indirect_attack",
}


class RatingInputGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._inputs = {}

        layout = QFormLayout(self)
        self._layout = layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(8)

        for field in ALL_RATING_FIELDS:
            spin_box = DecimalSpinBox()
            spin_box.setRange(0, 1000)
            spin_box.setDecimals(2)
            spin_box.setSingleStep(0.5)
            spin_box.setValue(float(DEFAULT_RATINGS[field] or 0.0))
            self._inputs[field] = spin_box
            layout.addRow(
                t(RATING_LABELS[field]),
                spin_box
            )

    def ratings(self):
        return {
            field: spin_box.value()
            for field, spin_box in self._inputs.items()
        }

    def set_ratings(self, ratings):
        for field, spin_box in self._inputs.items():
            spin_box.setValue(
                float(getattr(ratings, field, 0.0) or 0.0)
            )

    def set_rating_values(self, ratings):
        for field, spin_box in self._inputs.items():
            spin_box.setValue(
                float(ratings.get(field) or 0.0)
            )

    def update_rating_values(self, ratings):
        for field, value in ratings.items():
            if field in self._inputs:
                self._inputs[field].setValue(float(value))

    def rating_order(self):
        return tuple(self._inputs)

    def rating_labels(self):
        return {
            field: t(RATING_LABELS[field])
            for field in self._inputs
        }

    def retranslate_ui(self):
        for field in self._inputs:
            self._layout.labelForField(self._inputs[field]).setText(
                t(RATING_LABELS[field])
            )
