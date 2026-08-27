from PySide6.QtCore import QObject

from ht_coach_app.services.opponent_service import OpponentValidationError


class OpponentController(QObject):
    def __init__(self, view, service, app_events=None, parent=None):
        super().__init__(parent)
        self._view = view
        self._service = service
        self._app_events = app_events
        self._connect_view()
        self.refresh()

    def refresh(self, selected_name=None):
        opponents = self._service.list_opponents()
        self._view.set_opponents(
            opponents,
            selected_name=selected_name
        )

        if not opponents:
            self._view.clear_editor(
                self._service.default_ratings()
            )

    def _connect_view(self):
        self._view.new_requested.connect(
            self.new_opponent
        )
        self._view.save_requested.connect(
            self.save_opponent
        )
        if hasattr(self._view, "duplicate_requested"):
            self._view.duplicate_requested.connect(
                self.duplicate_opponent
            )
        self._view.delete_requested.connect(
            self.delete_opponent
        )
        if hasattr(self._view, "move_up_requested"):
            self._view.move_up_requested.connect(
                self.move_opponent_up
            )
        if hasattr(self._view, "move_down_requested"):
            self._view.move_down_requested.connect(
                self.move_opponent_down
            )
        self._view.selection_changed.connect(
            self.load_opponent
        )

    def new_opponent(self):
        self._view.clear_editor(
            self._service.default_ratings()
        )
        self._view.show_status(
            "New opponent ready."
        )

    def load_opponent(self, name):
        opponent = self._service.get_opponent(name)

        if opponent is None:
            self._view.clear_editor(
                self._service.default_ratings()
            )
            return

        self._view.set_current_opponent(
            opponent
        )

    def save_opponent(self):
        try:
            original_name = self._view.current_opponent_name()
            name, ratings = self._view.editor_data()

            if original_name:
                saved = self._service.update_opponent(
                    original_name,
                    name,
                    ratings
                )
            else:
                saved = self._service.create_opponent(
                    name,
                    ratings
                )

            self.refresh(
                selected_name=saved.name
            )
            self._publish_opponents_changed(
                "updated" if original_name else "created",
                original_name or "",
                saved.name
            )
            self._view.show_status(
                f"Saved opponent: {saved.name}"
            )
        except OpponentValidationError as exc:
            self._view.show_error(
                str(exc)
            )

    def duplicate_opponent(self):
        try:
            duplicated = self._service.duplicate_opponent(
                self._view.current_opponent_name()
            )
            self.refresh(
                selected_name=duplicated.name
            )
            self._publish_opponents_changed(
                "duplicated",
                "",
                duplicated.name
            )
            self._view.show_status(
                f"Duplicated opponent: {duplicated.name}"
            )
        except OpponentValidationError as exc:
            self._view.show_error(
                str(exc)
            )

    def delete_opponent(self):
        name = self._view.current_opponent_name()

        if not name:
            self._view.show_error(
                "Select an opponent to delete."
            )
            return

        if not self._view.confirm_delete(name):
            return

        try:
            next_selection = self._next_selection_after_delete(name)
            self._service.delete_opponent(name)
            self.refresh(selected_name=next_selection)
            self._publish_opponents_changed(
                "deleted",
                name,
                ""
            )
            self._view.show_status(
                f"Deleted opponent: {name}"
            )
        except OpponentValidationError as exc:
            self._view.show_error(
                str(exc)
            )

    def move_opponent_up(self):
        self._move_selected_opponent(
            self._service.move_opponent_up,
            "Moved opponent up."
        )

    def move_opponent_down(self):
        self._move_selected_opponent(
            self._service.move_opponent_down,
            "Moved opponent down."
        )

    def _move_selected_opponent(self, mover, status_message):
        name = self._view.current_opponent_name()

        if not name:
            self._view.show_error(
                "Select an opponent to reorder."
            )
            return

        try:
            moved = mover(name)
            if moved:
                self.refresh(selected_name=name)
                self._publish_opponents_changed(
                    "reordered",
                    name,
                    name
                )
                self._view.show_status(status_message)
        except OpponentValidationError as exc:
            self._view.show_error(
                str(exc)
            )

    def _next_selection_after_delete(self, name):
        opponents = self._service.list_opponents()
        names = [opponent.name for opponent in opponents]
        try:
            index = names.index(name)
        except ValueError:
            return None

        remaining = names[:index] + names[index + 1:]
        if not remaining:
            return None
        return remaining[min(index, len(remaining) - 1)]

    def _publish_opponents_changed(
        self,
        action,
        previous_name,
        current_name
    ):
        if self._app_events is not None:
            self._app_events.opponents_changed.emit(
                action,
                previous_name,
                current_name
            )
