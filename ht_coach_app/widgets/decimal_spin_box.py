import re

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QDoubleSpinBox

from ht_coach_app.core.localization import localization_service


class DecimalSpinBox(QDoubleSpinBox):
    def validate(self, text, position):
        stripped = str(text or "").strip()
        if stripped in {"", "+", "-"}:
            return QValidator.Intermediate, text, position
        if stripped.count(",") + stripped.count(".") > 1:
            return QValidator.Invalid, text, position
        if re.fullmatch(r"[+-]?\d*(?:[,.]\d*)?", stripped):
            value = self._text_to_float(stripped)
            if value is None:
                return QValidator.Intermediate, text, position
            if self.minimum() <= value <= self.maximum():
                return QValidator.Acceptable, text, position
            return QValidator.Intermediate, text, position
        return QValidator.Invalid, text, position

    def valueFromText(self, text):
        value = self._text_to_float(text)
        if value is None:
            return self.value()
        return value

    def textFromValue(self, value):
        text = f"{float(value):.{self.decimals()}f}"
        if localization_service().language == "es":
            return text.replace(".", ",")
        return text

    @staticmethod
    def _text_to_float(text):
        normalized = str(text or "").strip().replace(",", ".")
        if not normalized or normalized in {"+", "-", ".", "+.", "-."}:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None
