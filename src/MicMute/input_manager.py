"""Input management for MicMute.

This module provides the InputManager class for managing keyboard hooks
and processing input events from the hook thread.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer

from .core import signals, audio
from .utils import HookThread

__all__ = ["InputManager"]


class InputManager:
    """Manages the keyboard hook thread and event processing loop.

    This class handles starting and stopping the keyboard hook thread,
    and processes events from the hook's event queue on the main thread.

    Attributes:
        hook_thread: The thread running the keyboard hook.
        event_timer: Timer for polling the event queue.
    """

    def __init__(self) -> None:
        """Initialize the InputManager."""
        self.hook_thread: HookThread | None = None
        self.event_timer = QTimer()
        self.event_timer.setInterval(10)
        self.event_timer.timeout.connect(self.process_events)

    def start(self) -> None:
        """Start the hook thread and the event processing timer.

        Creates a new HookThread with the current hotkey configuration,
        starts it, and begins polling for events.
        """
        # Start Hook in Dedicated Thread
        # This prevents UI blocking from affecting hook latency
        self.hook_thread = HookThread(signals, audio.hotkey_config)
        self.hook_thread.start()

        # Wait for hook to install
        self.hook_thread.ready_event.wait(2.0)

        self.event_timer.start()

    def stop(self) -> None:
        """Stop the hook thread and event timer.

        Stops the event timer and signals the hook thread to stop.
        """
        self.event_timer.stop()
        if self.hook_thread:
            self.hook_thread.stop()

    def process_events(self) -> None:
        """Process events from the keyboard hook queue on the main thread.

        Polls the hook's event queue and dispatches events to the
        appropriate audio controller methods.
        """
        if (
            not self.hook_thread
            or not self.hook_thread.hook
            or self.hook_thread.hook.event_queue.empty()
        ):
            return

        try:
            while not self.hook_thread.hook.event_queue.empty():
                event = self.hook_thread.hook.event_queue.get_nowait()
                if event == "toggle":
                    audio.toggle_mute()
                elif event == "mute":
                    audio.set_mute_state(True)
                elif event == "unmute":
                    audio.set_mute_state(False)
        except Exception:
            # Silently ignore queue errors to prevent spam
            pass
