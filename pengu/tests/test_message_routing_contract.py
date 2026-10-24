"""Every bridge message type reaches the same handler (contract for the dispatch table)."""

import unittest
from unittest.mock import patch

from pengu.communication.message_handler import MessageHandler

# Captured from the if/elif router before it became a table (commit after b73ba87).
ROUTES = {
    "assistant-request": "_handle_assistant",
    "assistant-ranked": "_handle_assistant",
    "assistant-open-profile": "_handle_assistant",
    "assistant-opponent": "_handle_assistant",
    "assistant-runes-choose": "_handle_assistant",
    "assistant-runes-edit": "_handle_assistant",
    "assistant-runes-confirm": "_handle_assistant",
    "assistant-runes-back": "_handle_assistant",
    "assistant-items-import": "_handle_assistant",
    "assistant-items-choose": "_handle_assistant",
    "assistant-items-default": "_handle_assistant",
    "assistant-runes-keystone": "_handle_assistant",
    "assistant-lane": "_handle_assistant",
    "assistant-favorite": "_handle_assistant",
    "assistant-swiftplay-open": "_handle_assistant",
    "assistant-swiftplay-close": "_handle_assistant",
    "sexo2-library-request": "_handle_library",
    "sexo2-update-request": "_handle_sexo2_update",
    "sexo2-update-open": "_open_sexo2_updater",
    "friends-request": "_handle_friends",
    "chroma-log": "_handle_chroma_log",
    "request-local-preview": "_handle_request_local_preview",
    "request-local-asset": "_handle_request_local_asset",
    "chroma-selection": "_handle_chroma_selection",
    "dice-button-click": "_handle_dice_button_click",
    "settings-request": "_enqueue_settings",
    "path-validate": "_handle_path_validate",
    "open-mods-folder": "_handle_open_mods_folder",
    "request-skin-mods": "_handle_request_skin_mods",
    "request-manage-champion-mods": "_handle_request_manage_champion_mods",
    "request-manage-category-mods": "_handle_request_manage_category_mods",
    "request-maps": "_handle_request_maps",
    "request-fonts": "_handle_request_fonts",
    "request-announcers": "_handle_request_announcers",
    "request-category-mods": "_handle_request_category_mods",
    "select-skin-mod": "_handle_select_skin_mod",
    "select-map": "_handle_select_map",
    "select-font": "_handle_select_font",
    "select-announcer": "_handle_select_announcer",
    "select-other": "_handle_select_other",
    "open-logs-folder": "_handle_open_logs_folder",
    "diagnostics-request": "_handle_diagnostics_request",
    "diagnostics-clear": "_handle_diagnostics_clear",
    "stop-injection": "_handle_stop_injection",
    "diagnostics-delete": "_handle_diagnostics_delete",
    "diagnostics-clear-category": "_handle_diagnostics_clear_category",
    "diagnostics-clear-tracker": "_handle_diagnostics_clear_tracker",
    "diagnostics-apply-recommended": "_handle_diagnostics_apply_recommended",
    "open-pengu-loader-ui": "_handle_open_pengu_loader_ui",
    "settings-save": "_enqueue_settings",
    "settings-import-game": "_enqueue_settings",
    "language-save": "_handle_language_save",
    "add-custom-mods-category-selected": "_handle_add_custom_mods_category_selected",
    "add-custom-mods-champion-selected": "_handle_add_custom_mods_champion_selected",
    "add-custom-mods-skin-selected": "_handle_add_custom_mods_skin_selected",
    "find-match-hover": "_handle_find_match_hover",
    "dismiss-custom-mod": "_handle_dismiss_custom_mod",
    "delete-champion-mod": "_handle_delete_champion_mod",
    "delete-category-mod": "_handle_delete_category_mod",
    "rename-champion-mod": "_handle_rename_champion_mod",
    "rename-category-mod": "_handle_rename_category_mod",
    "dismiss-historic": "_handle_dismiss_historic",
    "party-enable": "_handle_party_enable",
    "party-disable": "_handle_party_disable",
    "party-add-peer": "_handle_party_add_peer",
    "party-remove-peer": "_handle_party_remove_peer",
    "party-reconnect": "_handle_party_reconnect",
    "party-get-state": "_handle_party_get_state",
    "swiftplay-pins-request": "_handle_swiftplay_pins",
    "swiftplay-pins-save": "_handle_swiftplay_pins",
}


class MessageRoutingContractTests(unittest.TestCase):
    def setUp(self):
        self.handler = MessageHandler.__new__(MessageHandler)

    def test_every_message_the_assistant_handles_is_routed(self):
        import re
        from pathlib import Path

        from pengu.communication.message_handler import _ROUTES

        source = (Path(__file__).parents[2] / "sexo2" / "services" / "assistant.py").read_text(encoding="utf-8")
        handled = set(re.findall(r'kind == "(assistant-[a-z-]+)"', source))
        self.assertTrue(handled)
        self.assertEqual(sorted(handled - set(_ROUTES)), [])  # a message nobody routes is dropped silently

    def test_each_type_calls_its_handler_with_the_payload(self):
        for message_type, method in ROUTES.items():
            payload = {"type": message_type, "marker": object()}
            with self.subTest(message_type), patch.object(MessageHandler, method) as handler:
                self.handler._route(message_type, payload)
                handler.assert_called_once_with(payload)

    def test_request_others_asks_for_the_others_category(self):
        self.handler.mod_storage = type("Storage", (), {"CATEGORY_OTHERS": "others"})()
        with patch.object(MessageHandler, "_handle_request_category_mods") as handler:
            self.handler._route("request-others", {"type": "request-others"})
        handler.assert_called_once_with({"category": "others"})

    def test_manual_skin_choice_marks_the_choice_manual(self):
        self.handler.shared_state = object()
        with patch("friends.selection_guard.mark_manual") as mark:
            self.handler._route("manual-skin-choice", {"type": "manual-skin-choice"})
        mark.assert_called_once_with(self.handler.shared_state)

    def test_untyped_skin_message_is_a_skin_detection(self):
        payload = {"skin": "Star Guardian Ahri"}
        with patch.object(MessageHandler, "_handle_skin_detection") as handler:
            self.handler._route(None, payload)
        handler.assert_called_once_with(payload)

    def test_unknown_type_does_nothing(self):
        with patch.object(MessageHandler, "_handle_skin_detection") as handler:
            self.handler._route("no-such-message", {"type": "no-such-message"})
        handler.assert_not_called()

    def test_game_config_import_returns_its_own_response(self):
        import json
        import threading
        from unittest.mock import Mock

        self.handler._background_lock = threading.Lock()
        self.handler._send_response = Mock()
        self.handler._settings_worker = Mock()
        self.handler._settings_worker.submit.side_effect = lambda work, failed: (work(), True)[1]
        with patch("sexo2.services.game_config.import_default", return_value={"success": True}) as apply:
            self.handler._enqueue_settings({"type": "settings-import-game", "requestId": "import-1", "confirmed": True})
        apply.assert_called_once_with(confirmed=True)
        response = json.loads(self.handler._send_response.call_args.args[0])
        self.assertEqual(response, {"type": "settings-game-imported", "requestId": "import-1", "success": True})

    def test_game_config_queue_failure_is_not_a_settings_snapshot(self):
        import json
        import threading
        from unittest.mock import Mock

        self.handler._background_lock = threading.Lock()
        self.handler._send_response = Mock()
        self.handler._settings_worker = Mock()
        self.handler._settings_worker.submit.return_value = False
        self.handler._enqueue_settings({"type": "settings-import-game", "requestId": "import-2"})
        response = json.loads(self.handler._send_response.call_args.args[0])
        self.assertEqual(response["type"], "settings-game-imported")
        self.assertEqual(response["requestId"], "import-2")
        self.assertFalse(response["success"])


if __name__ == "__main__":
    unittest.main()
