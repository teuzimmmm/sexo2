#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System tray manager for SEXO2
"""

import threading
import time
from pathlib import Path
from typing import Optional, Callable
import pystray
from PIL import Image, ImageDraw
from utils.core.logging import get_logger
from utils.core.paths import get_user_data_dir, open_folder_in_explorer
from config import (
    TRAY_THREAD_JOIN_TIMEOUT_S,
    TRAY_ICON_WIDTH,
    TRAY_ICON_HEIGHT,
    TRAY_ICON_ELLIPSE_COORDS,
    TRAY_ICON_BORDER_WIDTH,
    TRAY_ICON_FONT_SIZE,
    TRAY_ICON_TEXT_X,
    TRAY_ICON_TEXT_Y,
)

from sexo2.version import RELEASE_VERSION

log = get_logger()


class TrayManager:
    """Manages the system tray icon for SEXO2"""

    def __init__(self, quit_callback: Optional[Callable] = None, restart_callback: Optional[Callable] = None):
        """
        Initialize the tray manager

        Args:
            quit_callback: Function to call when user clicks "Quit"
            restart_callback: Function to call when user clicks "Restart"
        """
        self.quit_callback = quit_callback
        self.restart_callback = restart_callback
        self.icon = None
        self.tray_thread = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._locked_icon_image = None
        self._unlocked_icon_image = None
        self._base_icon_image = None  # Current base icon (locked or unlocked)
        self.stop_match_callback = None
        self.stop_match_available_callback = None
        self._current_status = "locked"
        self._issue_lock = threading.Lock()
        self._match_issue = None

    def _create_icon_image(self) -> Image.Image:
        """Create a simple icon image for the tray"""
        # Create a 128x128 icon with a simple design (doubled from 64x64)
        width, height = TRAY_ICON_WIDTH, TRAY_ICON_HEIGHT
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Draw a simple "S2" logo (Rose)
        # Background circle (scaled 2x)
        draw.ellipse(
            TRAY_ICON_ELLIPSE_COORDS, fill=(20, 24, 28, 255), outline=(190, 190, 190, 255), width=TRAY_ICON_BORDER_WIDTH
        )

        # "S2" text
        try:
            # Try to use a font if available
            from PIL import ImageFont

            font = ImageFont.truetype("arial.ttf", TRAY_ICON_FONT_SIZE)
        except (OSError, FileNotFoundError, ImportError) as e:
            log.debug(f"Could not load Arial font: {e}")
            # Fallback to default font
            font = ImageFont.load_default()
        except Exception as e:
            log.debug(f"Unexpected error loading font: {e}")
            # Fallback to default font
            font = ImageFont.load_default()

        # Draw "S2" text (scaled 2x)
        draw.text((TRAY_ICON_TEXT_X, TRAY_ICON_TEXT_Y), "S2", fill=(255, 255, 255, 255), font=font)

        return image

    def _load_icon_from_file(self, icon_name: str) -> Optional[Image.Image]:
        """Try to load icon from assets folder

        Args:
            icon_name: Name of the icon file (e.g., "tray_starting.png", "tray_ready.png")
        """
        try:
            # Use proper asset path resolution for PyInstaller compatibility
            from utils.core.paths import get_asset_path

            icon_path = get_asset_path(icon_name)

            if icon_path.exists():
                log.debug(f"Loading tray icon from: {icon_path}")
                with Image.open(icon_path) as img:
                    # Convert to RGBA and resize to 128x128 (doubled from 64x64)
                    img = img.convert("RGBA")
                    img = img.resize((128, 128), Image.Resampling.LANCZOS)
                    return img.copy()  # Return a copy to avoid issues with closed files
            else:
                log.warning(f"Icon '{icon_name}' not found at: {icon_path}")
        except Exception as e:
            log.error(f"Failed to load icon '{icon_name}': {e}")
        return None

    def _load_icons(self):
        """Load locked and unlocked icons"""
        # Load locked icon
        self._locked_icon_image = self._load_icon_from_file("tray_starting.png")

        # Load golden unlocked icon
        self._unlocked_icon_image = self._load_icon_from_file("tray_ready.png")

        # Fallback to icon.png if none exist
        if not self._locked_icon_image and not self._unlocked_icon_image:
            try:
                # Handle both frozen (PyInstaller) and development environments
                import sys

                if getattr(sys, "frozen", False):
                    # Running as compiled executable (PyInstaller)
                    base_dir = Path(sys.executable).parent
                    # Try multiple locations for PyInstaller
                    possible_paths = [
                        base_dir / "icon.png",  # Direct path
                        base_dir / "_internal" / "icon.png",  # _internal folder
                    ]
                else:
                    # Running as Python script
                    base_dir = Path(__file__).parent.parent
                    possible_paths = [base_dir / "icon.png"]

                # Try each possible path
                for icon_path_png in possible_paths:
                    if icon_path_png.exists():
                        log.debug(f"Loading fallback icon from: {icon_path_png}")
                        with Image.open(icon_path_png) as img:
                            img = img.convert("RGBA")
                            img = img.resize((128, 128), Image.Resampling.LANCZOS)
                            self._locked_icon_image = img.copy()
                            self._unlocked_icon_image = img.copy()
                        break
            except Exception as e:
                log.warning(f"Failed to load fallback icon: {e}")

    def _get_icon_image(self) -> Image.Image:
        """Get the icon image, trying file first, then creating a default one"""
        # Try to load icons from files
        self._load_icons()

        # Use locked icon as the initial base icon
        if self._locked_icon_image:
            return self._locked_icon_image

        # Fallback to created icon if no files found
        return self._create_icon_image()

    def _on_quit(self, icon, item):
        """Handle quit menu item click"""
        log.info("Quit requested from system tray")
        try:
            # Set stop event immediately to signal shutdown
            self._stop_event.set()

            # Call the quit callback (sets state.stop = True)
            if self.quit_callback:
                self.quit_callback()
        except SystemExit:
            # Handle sys.exit() calls gracefully
            log.info("System exit requested from quit callback")
        except Exception as e:
            log.error(f"Error in quit callback: {e}")
        finally:
            # Stop the tray icon (this will hide it from system tray)
            try:
                icon.stop()
                log.debug("Tray icon stopped from quit handler")
            except Exception as e:
                log.debug(f"Error stopping tray icon: {e}")

    def _on_icon_click(self, icon, item):
        """Handle left click on tray icon - do nothing"""
        # Left click does nothing, only right click shows menu
        pass

    def _on_settings(self, icon, item):
        """Open the injection threshold settings dialog."""
        log.info("Settings requested from system tray")
        try:
            from utils.integration.tray_settings import show_injection_settings_dialog

            show_injection_settings_dialog()
        except Exception as e:
            log.error(f"Failed to open settings dialog: {e}")
            try:
                from utils.system.admin_utils import show_message_box_threaded

                show_message_box_threaded(
                    f"Failed to open settings dialog:\n\n{e}",
                    "SEXO2 — Configurações",
                    0x10,  # MB_ICONERROR
                )
            except Exception:
                log.debug("Unable to show error message box for settings dialog failure")

    def _on_open_mods(self, icon, item):
        """Open the user mods folder in the file explorer."""
        log.info("Open Mods Folder requested from system tray")
        try:
            open_folder_in_explorer(get_user_data_dir() / "mods")
        except Exception as e:
            log.error(f"Failed to open mods folder: {e}")

    def _on_restart(self, icon, item):
        """Handle restart menu item click"""
        log.info("Restart requested from system tray")
        try:
            # Set stop event immediately to signal shutdown
            self._stop_event.set()

            # Call the restart callback
            if self.restart_callback:
                self.restart_callback()
        except SystemExit:
            # Handle sys.exit() calls gracefully
            log.info("System exit requested from restart callback")
        except Exception as e:
            log.error(f"Error in restart callback: {e}")
        finally:
            # Stop the tray icon (this will hide it from system tray)
            try:
                icon.stop()
                log.debug("Tray icon stopped from restart handler")
            except Exception as e:
                log.debug(f"Error stopping tray icon: {e}")

    def _on_stop_match(self, icon, item):
        if self._stop_match_enabled():
            self.stop_match_callback()
            if self.icon:
                self.icon.update_menu()

    def _stop_match_enabled(self):
        if not self.stop_match_callback:
            return False
        return self.stop_match_available_callback is None or self.stop_match_available_callback()

    def _on_show_match_issue(self, icon, item):
        with self._issue_lock:
            issue = dict(self._match_issue) if self._match_issue else None
        if not issue:
            return
        from utils.system.admin_utils import show_message_box_threaded

        count = f" (ocorreu {issue['count']} vezes)" if issue["count"] > 1 else ""
        show_message_box_threaded(
            f"{issue['summary']}{count}\n\n{issue['detail']}\n\n"
            "O SEXO2 só informa o que observou; a causa do fechamento pode ser desconhecida. "
            "Use 'Parar SEXO2 nesta partida' se precisar reconectar sem novas tentativas.",
            "SEXO2 - problema nesta partida",
            0x30,
        )

    def _on_open_logs(self, icon, item):
        open_folder_in_explorer(get_user_data_dir() / "logs")

    def _issue_menu_label(self):
        with self._issue_lock:
            issue = self._match_issue
            if issue:
                return f"⚠ {issue['summary'][:65]}"
        return "Nenhum problema detectado nesta partida"

    @staticmethod
    def _with_issue_badge(image):
        marked = image.copy()
        draw = ImageDraw.Draw(marked)
        width, height = marked.size
        diameter = max(12, width // 3)
        box = (width - diameter - 3, height - diameter - 3, width - 3, height - 3)
        draw.ellipse(box, fill=(210, 45, 35, 255), outline=(255, 255, 255, 255), width=3)
        return marked

    def _refresh_issue_display(self):
        icon = self.icon
        if not icon:
            return
        with self._issue_lock:
            has_issue = self._match_issue is not None
        base = self._unlocked_icon_image if self._current_status == "unlocked" else self._locked_icon_image
        base = base or self._base_icon_image
        try:
            if base:
                icon.icon = self._with_issue_badge(base) if has_issue else base
            icon.title = "SEXO2 - problema nesta partida" if has_issue else "SEXO2"
            icon.update_menu()
        except Exception as exc:
            log.debug("Could not refresh tray issue display: %s", exc)

    def report_match_issue(self, code: str, summary: str, detail: str):
        """Keep an observed failure visible without claiming its root cause."""
        now = time.monotonic()
        with self._issue_lock:
            previous = self._match_issue
            repeated = previous is not None and previous["code"] == code
            duplicate = repeated and now - previous["reported_at"] < 2.0
            count = previous["count"] + (0 if duplicate else 1) if repeated else 1
            self._match_issue = {
                "code": code,
                "summary": summary,
                "detail": detail,
                "count": count,
                "reported_at": now,
            }
        log.warning("[MATCH ISSUE] %s: %s", code, detail)
        self._refresh_issue_display()
        if self.icon and not repeated:
            try:
                self.icon.notify(summary, "SEXO2 - problema na partida")
            except Exception as exc:
                log.debug("Tray notification unavailable: %s", exc)

    def clear_match_issue(self):
        with self._issue_lock:
            self._match_issue = None
        self._refresh_issue_display()

    def _create_menu(self) -> pystray.Menu:
        """Create the context menu for the tray icon"""
        return pystray.Menu(
            pystray.MenuItem(f"SEXO2 {RELEASE_VERSION}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Abrir pasta de mods", self._on_open_mods),
            pystray.MenuItem(
                lambda item: self._issue_menu_label(),
                self._on_show_match_issue,
                enabled=lambda item: self._match_issue is not None,
            ),
            pystray.MenuItem("Abrir pasta dos logs", self._on_open_logs),
            pystray.MenuItem(
                lambda item: (
                    "SEXO2 parado nesta partida"
                    if self.stop_match_callback and not self._stop_match_enabled()
                    else "Parar SEXO2 nesta partida"
                ),
                self._on_stop_match,
                enabled=lambda item: self._stop_match_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Reiniciar SEXO2", self._on_restart),
            pystray.MenuItem("Sair", self._on_quit),
        )

    def _run_tray(self):
        """Run the tray icon in a separate thread"""
        try:
            # Store base icon for later use
            self._base_icon_image = self._get_icon_image()
            icon_image = self._base_icon_image
            menu = self._create_menu()

            self.icon = pystray.Icon("SEXO2", icon_image, "SEXO2", menu, default_action=self._on_icon_click)

            log.info("System tray icon started")
            # Use run_detached to prevent blocking the main thread
            self.icon.run_detached()
            self._ready_event.set()
            self._refresh_issue_display()
        except Exception as e:
            log.error(f"Failed to start system tray: {e}")

    def start(self):
        """Start the system tray icon"""
        if self._ready_event.is_set() or (self.tray_thread and self.tray_thread.is_alive()):
            log.warning("System tray is already running")
            return

        try:
            self._stop_event.clear()
            self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
            self.tray_thread.start()
            log.info("System tray manager started - no console window")
        except Exception as e:
            log.error(f"Failed to start system tray manager: {e}")

    def stop(self):
        """Stop the system tray icon"""
        self._stop_event.set()
        self._ready_event.clear()
        if self.icon:
            try:
                self.icon.stop()
                log.info("System tray icon stopped")
            except Exception as e:
                log.error(f"Failed to stop system tray icon: {e}")

        if self.tray_thread and self.tray_thread.is_alive():
            self.tray_thread.join(timeout=TRAY_THREAD_JOIN_TIMEOUT_S)

    def is_running(self) -> bool:
        """Check if the tray icon is running"""
        return self.icon is not None and self._ready_event.is_set() and not self._stop_event.is_set()

    def wait_for_quit(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for quit signal from tray

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if quit was requested, False if timeout
        """
        return self._stop_event.wait(timeout)

    def set_status(self, status: str):
        """
        Update the tray icon to show the specified status

        Args:
            status: "locked" or "unlocked"
        """
        if status not in ("locked", "unlocked"):
            log.warning("Unknown tray status: %s", status)
            return
        # Remember early startup status; the tray backend applies it when ready.
        # An icon is presentation only and must never stall initialization.
        if status == self._current_status and self.icon and self._base_icon_image:
            return
        self._current_status = status
        self._refresh_issue_display()

    def set_downloading(self, is_downloading: bool):
        """
        Update the tray icon to show downloading status (legacy method for compatibility)

        Args:
            is_downloading: True to show locked icon, False to show golden unlocked icon
        """
        if is_downloading:
            self.set_status("locked")
        else:
            self.set_status("unlocked")
