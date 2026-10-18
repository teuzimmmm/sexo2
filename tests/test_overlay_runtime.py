"""Overlays switched on and off from Configurações without restarting (D-117)."""

import unittest
from unittest.mock import patch

from sexo2.overlay import runtime


class FakeThread:
    def __init__(self):
        self.alive = False
        self.stopped = False

    def start(self):
        self.alive = True

    def is_alive(self):
        return self.alive

    def stop(self):
        self.stopped = True
        self.alive = False


class FakeManager:
    def __init__(self):
        self.registered = []

    def register(self, name, thread, stop_method=None):
        self.registered.append(name)


class OverlayRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.config = {"gold": True, "augments": False}
        self.created = []

        def create(kind, state, lcu):
            thread = FakeThread()
            self.created.append((kind, thread))
            return f"{kind} overlay", thread

        patches = [
            patch.object(runtime, "enabled", side_effect=lambda kind: self.config[kind]),
            patch.object(runtime, "_create", side_effect=create),
            patch.object(runtime, "_threads", {}),
            patch.object(runtime, "_context", None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.manager = FakeManager()

    def test_startup_registers_only_the_enabled_overlays_for_the_manager_to_start(self):
        runtime.setup(self.manager, "state", "lcu")
        self.assertEqual(self.manager.registered, ["gold overlay"])
        self.assertFalse(self.created[0][1].alive)

    def test_saving_starts_and_stops_overlays_to_match(self):
        runtime.setup(self.manager, "state", "lcu")
        gold = self.created[0][1]
        gold.start()  # the manager's start_all
        self.config.update(gold=False, augments=True)
        runtime.apply()
        self.assertTrue(gold.stopped)
        augments = self.created[1][1]
        self.assertEqual(self.created[1][0], "augments")
        self.assertTrue(augments.alive)
        runtime.apply()  # nothing changed: nothing new
        self.assertEqual(len(self.created), 2)

    def test_apply_before_startup_does_nothing(self):
        runtime.apply()
        self.assertEqual(self.created, [])


if __name__ == "__main__":
    unittest.main()
