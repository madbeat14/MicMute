# Changelog
All notable changes to this project will be documented in this file.

## [2.0.0] - 2025-11-28
### Features
- **Modern UI**: Replaced "Star" default indicator with a modern "DEFAULT" badge (Blue Pill style).
- **Advanced Sync**: Implemented "Absolute State Matching" to ensure synced devices always match the Master's state.
- **System Integration**: "Set as Default" now updates the Windows System Default Device using `IPolicyConfig`.
- **Auto-Detection**: Application now prioritizes and syncs with the actual Windows Default Device on startup/refresh.
- **Singleton Dialogs**: Prevented multiple instances of Settings/Selection windows from opening.

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
