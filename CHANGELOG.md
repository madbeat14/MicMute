

## [2.5.0] - 2025-11-29
### Performance
- **Hook Thread**: Moved Windows Keyboard Hook to a dedicated thread with its own message loop. This completely isolates input handling from the main application thread, eliminating hook timeouts.
- **Process Priority**: Added automatic process priority elevation (High) to prevent CPU starvation and input lag during high-load scenarios (e.g., gaming).
- **Audio Feedback**: Moved `winsound.Beep` calls to a background thread to prevent blocking the main event loop during mute toggles.

### Fixes
- **Input Leakage**: Fixed critical issue where rapid hotkey presses caused the original key action (e.g., Media Play/Pause) to leak through to other applications.
- **Gaming Freeze**: Fixed issue where using the hotkey while holding movement keys (WASD) in games caused the character to get stuck moving in one direction.

## [2.4.0] - 2025-11-29
### Features
- **Device Selection**: Added "Monitor Device" selector to Persistent Overlay settings, allowing users to choose a specific microphone for the voice activity meter.

### Fixes
- **Voice Activity Meter**: Fixed issue where voice activity meter was monitoring the default system device instead of the active microphone.
- **GUI**: Resolved syntax error in GUI settings widget.

### Refactor
- **COM Interfaces**: Extracted COM definitions to `src/MicMute/com_interfaces.py` and added `IPropertyStore` for device name retrieval.
- **Utils**: Added `get_audio_devices` utility to enumerate active capture devices with friendly names.

## [2.3.0] - 2025-11-29
### Performance
- **CPU Optimization**: Implemented dynamic throttling for AFK detection, reducing idle CPU usage to near zero.
- **RAM Optimization**: Added lazy loading for Settings Window (saving ~10-20MB startup RAM) and `__slots__` for AudioController.
- **GUI Optimization**: Implemented asset caching for OSD icons to prevent disk I/O on every mute toggle.

### Stability
- **Crash Fix**: Resolved a crash related to `__slots__` and PySide signal connections by adding `__weakref__`.

## [2.2.0] - 2025-11-29
### Fixes
- **Voice Activity Meter**: Replaced `pycaw` dependency with robust direct COM implementation to fix detection issues.

### Refactor
- **COM Interfaces**: Extracted COM definitions to `src/MicMute/com_interfaces.py` for better maintainability.

### Documentation
- **Code Comments**: Added detailed documentation and references for all used COM GUIDs.

### Fixes
- **Sync Timing**: Fixed issue where UI updated before devices were actually muted.
- **Crash Fix**: Resolved `RuntimeError` and `NameError` when reopening dialogs after closure.
- **Dependencies**: Added missing `comtypes` imports and defined `WAVEFORMATEX`/`PROPERTYKEY` structures manually to fix `AttributeError`.

### Refactor
- Renamed "Sync" column to "Link Mute" for clarity.
- Refactored `main.py` to use singleton pattern for dialog management.

## [1.10.0] - 2025-11-28
### Refactor
- Unified Settings UI with tabbed interface (General, Audio, Misc, Overlay).

### Features
- Added "Metro-style" On-Screen Display (OSD) with customizable size and position (9 anchor points).
