"""MicMute - A lightweight microphone mute toggle application.

MicMute is a system tray application that provides quick microphone
muting/unmuting functionality with support for global hotkeys, OSD
notifications, and persistent overlay indicators.

Example:
    To run the application::

        from MicMute import main
        main()

Or from command line::

    python -m MicMute
"""

from __future__ import annotations

try:
    from ._version import __version__
except ImportError:
    # Fallback if package is not installed in development mode
    __version__ = "0.0.0+dev"

from .main import main

__author__ = "madbeat14"

__all__ = ["main", "__version__"]
