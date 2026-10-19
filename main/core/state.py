#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application state management
"""


class AppState:
    """Application state to replace global variables"""

    def __init__(self):
        self.shutting_down = False
        self.lock_file = None
        self.lock_file_path = None

        # The OS mutex handles (current and legacy name), kept alive for the lifetime of the process
        self.mutex_handle = None


# Global app state instance
_app_state = AppState()


def get_app_state() -> AppState:
    """Get the global application state instance"""
    return _app_state
