from PySide6.QtCore import QTimer
from .utils import HookThread
from .core import signals, audio

class InputManager:
    """
    Manages the keyboard hook thread and event processing loop.
    """
    def __init__(self):
        """
        Initializes the InputManager.
        """
        self.hook_thread = None
        self.event_timer = QTimer()
        self.event_timer.setInterval(10)
        self.event_timer.timeout.connect(self.process_events)

    def start(self):
        """
        Starts the hook thread and the event processing timer.
        """
        # Start Hook in Dedicated Thread
        # This prevents UI blocking from affecting hook latency
        self.hook_thread = HookThread(signals, audio.hotkey_config)
        self.hook_thread.start()
        
        # Wait for hook to install
        self.hook_thread.ready_event.wait(2.0)
        
        self.event_timer.start()

    def stop(self):
        """
        Stops the hook thread and event timer.
        """
        self.event_timer.stop()
        if self.hook_thread:
            self.hook_thread.stop()

    def process_events(self):
        """
        Processes events from the keyboard hook queue on the main thread.
        """
        # Access queue via hook_thread.hook
        if self.hook_thread and self.hook_thread.hook and not self.hook_thread.hook.event_queue.empty():
            try:
                while not self.hook_thread.hook.event_queue.empty():
                    event = self.hook_thread.hook.event_queue.get_nowait()
                    if event == 'toggle':
                        audio.toggle_mute()
                    elif event == 'mute':
                        audio.set_mute_state(True)
                    elif event == 'unmute':
                        audio.set_mute_state(False)
            except: pass
