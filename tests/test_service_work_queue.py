import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sexo2.services.work_queue import SerialWorker
from pengu.communication.message_handler import MessageHandler


class WorkQueueTests(unittest.TestCase):
    def test_a_blocked_action_has_bounded_backlog_and_preserves_saves(self):
        worker = SerialWorker("test-panel", capacity=2)
        release = threading.Event()
        entered = threading.Event()
        actions = []

        def blocked():
            entered.set()
            release.wait(2)

        try:
            self.assertTrue(worker.submit(blocked, self.fail))
            self.assertTrue(entered.wait(1))
            self.assertTrue(worker.submit(lambda: actions.append("save A"), self.fail))
            self.assertTrue(worker.submit(lambda: actions.append("save B"), self.fail))
            self.assertFalse(worker.submit(lambda: actions.append("overflow"), self.fail))
        finally:
            release.set()
            self.assertTrue(worker.close(timeout=2))
        self.assertEqual(actions, ["save A", "save B"])
        self.assertFalse(worker.submit(lambda: None, self.fail))

    def test_failed_action_and_response_do_not_kill_later_actions(self):
        worker = SerialWorker("test-panel")
        actions = []

        def broken():
            raise RuntimeError("synthetic failure")

        def broken_response(error):
            raise RuntimeError("synthetic response failure")

        with self.assertLogs("sexo2.services.work_queue", level="ERROR"):
            worker.submit(broken, broken_response)
            worker.submit(lambda: actions.append("saved"), self.fail)
            self.assertTrue(worker.close(timeout=2))
        self.assertEqual(actions, ["saved"])

    def test_swiftplay_save_failure_is_answered_and_next_request_works(self):
        handler = MessageHandler.__new__(MessageHandler)
        handler._background_lock = threading.Lock()
        handler.skin_scraper = None
        handler.shared_state = SimpleNamespace()
        responses = []
        handler._send_response = lambda message: responses.append(json.loads(message))
        service = Mock()
        service.save.side_effect = RuntimeError("synthetic disk failure")
        service.snapshot.return_value = {"type": "swiftplay-pins-state"}
        with patch("pengu.processing.swiftplay_pins.SwiftplayPanelService", return_value=service):
            handler._handle_swiftplay_pins({"type": "swiftplay-pins-save", "requestId": "save"})
            handler._handle_swiftplay_pins({"type": "swiftplay-pins-request", "requestId": "read"})
            self.assertTrue(handler._swiftplay_worker.close(timeout=2))
        self.assertEqual([r["requestId"] for r in responses], ["save", "read"])
        self.assertEqual(responses[0]["type"], "swiftplay-pins-error")
        self.assertEqual(responses[1]["type"], "swiftplay-pins-state")


if __name__ == "__main__":
    unittest.main()
