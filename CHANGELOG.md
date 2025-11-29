
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
