"""Opt-in ready-check acceptance; never starts a queue or accepts outside ReadyCheck."""

import time
import threading


class AutoAccept:
    def __init__(self, lcu):
        self.lcu = lcu
        self.enabled = False
        self.accepted = False
        self.attempts = 0
        self.next_attempt = 0
        self.message = ""
        self.lock = threading.RLock()

    def tick(self, phase):
        with self.lock:
            self._tick(phase)

    def _tick(self, phase):
        if phase != "ReadyCheck":
            self.accepted = False
            self.attempts = 0
            self.next_attempt = 0
            return
        if not self.enabled or self.accepted or self.attempts >= 3 or time.monotonic() < self.next_attempt:
            return
        if not self.lcu or not self.lcu.ok:
            return
        check = self.lcu.get("/lol-matchmaking/v1/ready-check")
        if not isinstance(check, dict) or check.get("state") != "InProgress":
            return
        if check.get("playerResponse") not in ("None", "Pending", None):
            return
        if self.lcu.get("/lol-gameflow/v1/gameflow-phase") != "ReadyCheck":
            return
        self.attempts += 1
        self.next_attempt = time.monotonic() + 2
        try:
            success = self.lcu.accept_ready_check()
            if success:
                self.accepted = True
                self.message = "Partida aceita automaticamente."
            else:
                self.message = "Autoaceite não confirmado; aceite manualmente."
        except Exception:
            self.message = "Autoaceite não confirmado; aceite manualmente."
