from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QWidget,
)

from ht_coach_app.services.opponent_service import (
    ALL_RATING_FIELDS,
    DEFAULT_RATINGS,
)


RATING_LABELS = {
    "left_defense": "Left defense",
    "central_defense": "Central defense",
    "right_defense": "Right defense",
    "midfield": "Midfield",
    "left_attack": "Left attack",
    "central_attack": "Central attack",
    "right_attack": "Right attack",
    "indirect_defense": "Indirect defense",
    "indirect_attack": "Indirect attack",
}


class RatingInputGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._inputs = {}

        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(8)

        for field in ALL_RATING_FIELDS:
            spin_box = QDoubleSpinBox()
            spin_box.setRange(0, 1000)
            spin_box.setDecimals(2)
            spin_box.setSingleStep(0.5)
            spin_box.setValue(float(DEFAULT_RATINGS[field] or 0.0))
            self._inputs[field] = spin_box
            layout.addRow(
                RATING_LABELS[field],
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
