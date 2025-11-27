# MicMute

Microphone Mute Toggle - Final Version (PySide6/Qt + Native Hooks)

## Features
- Configurable Hotkey (Dropdown or Capture)
- Advanced Beep Configuration (Freq, Duration, Count)
- Configurable Beep Sounds (Toggle in Tray Menu)
- NO 'keyboard' library dependency (Uses native Windows Hooks via ctypes)
- Single-Threaded Architecture (Hooks integrate with Qt Event Loop)
- Event-driven Theme Detection (0% idle CPU)
- Aggressive Memory Management
- System tray icon using SVG files
- "Select Microphone" dialog
- Persists selection and settings to `mic_config.json`

## Installation

```bash
pip install -e .
```

## Usage

Run the application:

```bash
micmute
```

Or from python:

```python
from MicMute.main import main
main()
```
