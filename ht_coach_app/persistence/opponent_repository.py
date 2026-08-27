from engine.opponents.opponent_manager import OpponentManager
from ht_coach_app.core.paths import user_data_dir


class OpponentRepository:
    def __init__(self, storage_path=None):
        self.storage_path = storage_path or (
            user_data_dir() / "opponents.json"
        )
        self._manager = OpponentManager(
            self.storage_path
        )

    def list_opponents(self):
        return self._manager.list_opponents()

    def list_opponents_by_recency(self):
        return self._manager.list_opponents_by_recency()

    def get(self, name):
        return self._manager.get(name)

    def save(self, opponent):
        return self._manager.save(opponent)

    def delete(self, name):
        return self._manager.delete(name)

    def move_up(self, name):
        return self._manager.move_up(name)

    def move_down(self, name):
        return self._manager.move_down(name)
