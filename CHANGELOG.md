# Changelog

## [2.13.0] - 2025-11-29
### Features
- **Tray Menu Refactor**: Reorganized the system tray menu for better usability. Added "Start on Boot", "Help", and "About" options.
- **High Priority Startup**: Replaced Registry-based startup with Windows Task Scheduler. "Start on Boot" now creates a task with "Highest Privileges" and Real-time priority (Priority 0).
- **UAC Elevation**: Added automatic UAC elevation request if creating the startup task fails due to permissions.
- **Silent Startup**: Uses `pythonw.exe` when running from source to prevent console window on startup.

### Fixes
- **Tooltip Regression**: Fixed an issue where the tray icon tooltip did not display the mute status on application start.
- **Source Mode Startup**: Fixed "Start on Boot" not passing the script path correctly when running from source.

## [2.12.0] - 2025-11-29
### Features
- **Audio Mode Selection**: Added option to choose between "Beeps" (default) and "Custom Sounds" for audio feedback.
- **Custom Sound Volume**: Added volume controls (0-200%) for custom mute and unmute sounds, allowing for software amplification.
- **Default Device Icon**: Replaced the text-based star indicator with a standard checkmark icon for the default device in the device list.

### Fixes
- **Volume Application**: Fixed issue where volume changes for custom sounds were not applied instantly to hotkey actions.

## [2.11.0] - 2025-11-29
### Features
- **Hybrid Asset Management**: Added support for importing custom sound files (`.wav`, `.mp3`). Imported sounds are copied to a local `micmute_sounds/` directory for portability.
- **Opacity Controls**: Added opacity sliders and spinboxes (10-100%) to both the On-Screen Display (OSD) and Persistent Overlay settings.
- **Improved Settings UI**: Replaced text inputs with dropdowns for sound selection and added "Import" and "Preview" buttons.

## [2.10.0] - 2025-11-29
### Features
- **Instant Apply Settings**: Removed "Save" button. All settings changes now apply immediately for a more responsive experience.
- **Bi-Directional Sync**: Settings UI and System Tray menu are now perfectly synchronized. Toggling an option in one updates the other instantly.
- **Soft Dependency**: The "Show Voice Activity Meter" setting is now preserved even when the Persistent Overlay is disabled.
- **Resource Optimization**: The audio meter thread is now automatically stopped when the overlay is hidden, reducing CPU usage.

### Changed
- **Tray Menu**: Renamed "Play Beep Sounds" to "Play Sound on Toggle" and grouped overlay options for better usability.
- **Settings UI**: Refactored to use centralized signals for configuration updates.

## [2.9.1] - 2025-11-29
### Added
- **Sound Persistence**: Custom sound files are now automatically copied to a local `sounds/` directory on save, ensuring portability and persistence even if the original file is deleted.
- **Robust Audio Fallback**: The application now gracefully falls back to system beeps if a custom sound file is missing or fails to play.

### Fixed
- **Custom Sound UI**: Resolved an issue where the "Unmute Sound" option was hidden in the settings dialog.
- **Settings UI**: The settings dialog now displays only the filename of custom sounds for a cleaner look.

### Changed
- **Build Configuration**: Updated `MicMute.spec` to include necessary hidden imports (`comtypes`, `pycaw`, `winsound`) for reliable EXE building.

## [2.9.0] - 2025-11-29
### Added
- **Modular Architecture**: Refactored monolithic `gui.py` into a structured `gui/` package with separate modules for devices, hotkeys, settings, and themes.
- **Overlay Settings**:
    - Added "Position Mode" dropdown (Custom vs. 9 Predefined positions).
    - Added "Size" slider (50% - 200%) synchronized with a pixel height input.
- **OSD Settings**:
    - Added "Size" slider and pixel input.
    - Added "Position" dropdown (Top, Center, Bottom).
- **UX Improvements**:
    - Split "Save & Close" into separate "Save" (Apply) and "Close" buttons in Settings.

### Changed
- Moved configuration logic from `core.py` to `config.py`.
- Moved hook handling to `input_manager.py`.

## [2.8.2] - 2025-11-29
### Documentation
- **Comprehensive Docstrings**: Added standard Python docstrings to all classes and functions in `core.py`, `gui.py`, `main.py`, `overlay.py`, and `utils.py`.
- **PEP 8 Comments**: Refactored inline comments to the preceding line across the codebase for improved readability and PEP 8 compliance.

## [2.8.1] - 2025-11-29
### Tests
- **Comprehensive Test Suite**: Implemented full unit test coverage for Core, GUI, Overlay, and Utility components (22 tests).
- **Warning Resolution**: Resolved 52 `COMError` warnings in `DeviceSelectionWidget` by correctly mocking global audio dependencies.
- **Stability**: Refactored tests to use safe `patch` context managers instead of risky `sys.modules` patching.

## [2.8.0] - 2025-11-29
### Features
- **Device Synchronization**: Implemented real-time detection of Default Recording Device changes. The application now automatically switches its control target and updates the UI (Tray Menu and Settings) instantly when the default device is changed in Windows Settings.
- **Background Watcher**: Added `IMMNotificationClient` COM listener to watch for device changes without polling.

## [2.7.0] - 2025-11-29
### Debugging
- **Pycaw Scripts**: Added `debug_audio_pycaw.py` and `debug_meter_pycaw.py` as high-level alternatives using the pycaw library for device enumeration and metering.

## [2.6.0] - 2025-11-29
### Fixes
- **Voice Activity Meter**: Fixed issue where the meter would not initialize on some devices by ensuring `IAudioClient` is active.
- **Device Names**: Fixed `Unknown Device` issue by using robust COM casting to retrieve friendly names (e.g., "Microphone (Realtek Audio)").
- **Crash Fix**: Resolved `NameError` in `overlay.py` caused by missing import.

### Debugging
- **Debug Scripts**: Enhanced `debug_audio.py` and `debug_meter.py` with detailed comments and improved device enumeration logic.

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
