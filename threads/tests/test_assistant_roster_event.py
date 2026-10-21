"""The champion-select roster signal is sent only when the roster changes (D-140)."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from threads.websocket.websocket_event_handler import WebSocketEventHandler


def session(champion=86, puuid="p-1"):
    return {
        "id": "cs-1",
        "localPlayerCellId": 2,
        "myTeam": [
            {"cellId": 1, "championId": champion, "championPickIntent": 0, "assignedPosition": "top", "puuid": puuid},
            {"cellId": 2, "championId": 103, "championPickIntent": 0, "assignedPosition": "middle", "puuid": "p-2"},
        ],
        "theirTeam": [],
    }


class AssistantRosterEventTests(unittest.TestCase):
    def setUp(self):
        self.ui = MagicMock()
        self.state = SimpleNamespace(local_cell_id=2, players_visible=2, ui_skin_thread=self.ui)
        self.handler = WebSocketEventHandler(MagicMock(), self.state)

    def event(self, data):
        self.handler.handle_api_event({"uri": "/lol-champ-select/v1/session", "data": data})

    def test_the_same_roster_is_broadcast_once(self):
        self.event(session())
        self.event(session())
        self.ui._broadcast_assistant_roster.assert_called_once_with()

    def test_a_champion_or_player_change_broadcasts_again(self):
        self.event(session())
        self.event(session(champion=1))
        self.event(session(puuid="p-other"))
        self.assertEqual(self.ui._broadcast_assistant_roster.call_count, 3)

    def test_without_a_ui_thread_the_event_is_ignored(self):
        self.state.ui_skin_thread = None
        self.event(session())  # must not raise


if __name__ == "__main__":
    unittest.main()
