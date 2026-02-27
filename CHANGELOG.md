# Changelog

## [2.14.0] - 2026-02-27
### Features
- **Adaptive Overlay Icon**: The Persistent Overlay now automatically adapts its icon color (light or dark) based on the background brightness for optimal visibility. It periodically samples the screen area behind the overlay and uses a perceived luminance formula with hysteresis to avoid flickering.

### Tests
- **Adaptive Icon Testing**: Added 8 new tests to `test_overlay.py` covering background sampling mocks, hysteresis logic, and backward compatibility.

## [2.13.13] - 2026-02-27
### Fixed
- **Persistent Overlay Topmost**: Resolved multiple edge cases where the overlay could lose its always-on-top position.
    - **Removed rate-limiter**: `_force_topmost()` no longer has an internal 500ms skip gate — every timer tick actually calls `SetWindowPos`, preventing gaps in Z-order reassertion.
    - **Z-order verification**: `_visibility_check()` now reads `WS_EX_TOPMOST` via `GetWindowLongW`. If the style was stripped by another application, it immediately re-asserts topmost.
    - **Post-drag reassertion**: `_force_topmost()` is called after every mouse drag release so the overlay doesn't lose topmost status during repositioning.
    - **Instant show reassertion**: `showEvent` now calls `_force_topmost()` directly instead of via a 50ms `QTimer.singleShot` delay.
    - **Faster recovery**: Topmost reassertion timer interval reduced from 1000ms to 500ms for quicker recovery after another window takes the foreground.
- **Auto-restore improvement**: `_visibility_check()` now also calls `_force_topmost()` when restoring from hidden or minimized state.

## [2.13.12] - 2026-02-26
### Performance
- **Pixmap Caching**: `StatusOverlay` now caches `QIcon.pixmap()` results. Previously a new `QIcon` object was created on every mute toggle; now icons are rendered once and reused.
- **Monotonic Timing**: Replaced `time.time()` with Qt's `QElapsedTimer` in `_force_topmost()` for a precise, syscall-free rate limiter.
- **Device Enumeration**: `set_mute_state()` now enumerates all audio devices once and matches all synced slaves in a single pass instead of calling `GetAllDevices()` once per slave.
- **Module-Level Imports**: Moved `get_internal_asset` / `get_external_sound_dir` from a per-call lazy import inside `play_sound()` to module-level in `core.py`.

### Code Quality
- **Deduplication**: Extracted `_update_and_save()` helper in `AudioController` — eliminates 7 nearly-identical `update_*_config` methods.
- **Removed Duplicate TypedDicts**: `BeepConfig`, `SoundConfig`, `HotkeyConfig` were defined in both `core.py` and `config.py`. `core.py` now imports them from `config.py`.
- **Resource Safety**: `audio_client` is now initialized to `None` in `StatusOverlay.__init__`, removing the `hasattr` guard in `stop_meter()`.
- **Signal Cleanup**: Worker signals (`peak_detected`, `error_occurred`) are explicitly disconnected before the worker is stopped to prevent stale deliveries.
- **Consolidated Cleanup**: `set_config()` disabled-state cleanup (hide, stop_meter, stop timers) merged into a single `else` branch.
- **Dead Code**: Removed redundant `import os` inside `_setup_qt_environment()` (already imported at module level).

## [2.13.8] - 2026-02-01
### Improved
- **Area-Specific Topmost Checking**: Overlay now only forces topmost when something is actually covering its screen area.
    - Uses `WindowFromPoint` to check center and corners of overlay.
    - If you have another topmost window (like Terminal) in a different area of the screen, it won't trigger the overlay.
    - Only reacts when the overlay's specific location is obscured.

## [2.13.7] - 2026-02-01
### Fixed
- **winreg Import**: Fixed missing `winreg` import in `utils.py` that caused theme detection to fail.
- **Persistent Overlay Topmost**: Significantly improved overlay visibility reliability.
    - Increased topmost assertion frequency from 250ms to 100ms for faster response.
    - Added visibility monitor timer (500ms) to auto-restore overlay if it becomes hidden while enabled.
    - Added area-specific topmost checking using `WindowFromPoint` - only forces topmost when something actually covers the overlay's screen area.
    - Added `BringWindowToTop` fallback technique for better compatibility with fullscreen games.
    - Re-applies Qt window flags when overlay loses topmost status.

## [2.13.5] - 2026-01-03
### Fixed
- **Persistent Overlay**: Fixed issue where overlay would not reliably stay on top of all windows, including fullscreen games.
    - Implemented Windows API `SetWindowPos` with `HWND_TOPMOST` flag for forced topmost positioning.
    - Added periodic re-assertion timer (every 2 seconds) to maintain topmost Z-order.
    - Added `Qt.WindowDoesNotAcceptFocus` flag to prevent stealing focus from other applications.
    - Resource efficient: ~0.005% CPU overhead, 0 bytes additional RAM.

### Added
- **Build Tooling**: Created automated spec file generator (`generate_spec.py`) for portable builds across different environments.
- **Developer Workflow**: Added `dev_build.py` script for maintainers to upgrade dependencies, sync, lock, and build in one command.
- **Documentation**: Updated README with reproducible build instructions and build script documentation.

### Changed
- **Dependencies**: Pinned minimum versions (PySide6>=6.10.1, pycaw>=20251023) for better reproducibility.

## [2.13.4] - 2026-01-03
### Fixes
- **Persistent Overlay**: Resolved an issue where the overlay would not appear on application startup even if enabled.
    - Added explicit state synchronization during application initialization.
    - Improved robustness of audio meter activation by relying on configuration state instead of widget visibility.

## [2.13.3] - 2025-11-30
### Features
- **Voice Meter Sensitivity**: Added a sensitivity slider (1-100%) to the Persistent Overlay settings. This allows users to adjust the volume threshold required to trigger the voice activity LED.

## [2.13.2] - 2025-11-30
### Fixes
- **Visuals**: Fixed critical bugs in OSD and Persistent Overlay positioning logic.
    - **Positioning**: Now correctly accounts for the Windows Taskbar using `availableGeometry()`.
    - **Live Updates**: Sliders (Size, Opacity) and "Lock Position" checkbox now update the overlay immediately.
    - **Locking**: "Lock Position" now correctly prevents dragging, and dragging (when unlocked) automatically switches to "Custom" mode.

## [2.13.1] - 2025-11-29
### Maintenance
- **Environment**: Pinned Python version to 3.14 using `uv` and updated dependencies.

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
