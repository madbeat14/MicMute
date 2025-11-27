# MicMute

Microphone Mute Toggle - Final Version (PySide6/Qt + Native Hooks)

## Features
- **Configurable Hotkey**: Choose from a dropdown or capture any key.
- **Advanced Beep Configuration**: Customize frequency, duration, and count for mute/unmute events.
- **System Tray Integration**: Control everything from the tray icon.
- **Native Hooks**: Uses low-level Windows hooks (ctypes) for reliable hotkey detection without admin privileges.
- **Zero Dependencies** (Runtime): No 'keyboard' library required.
- **Theme Aware**: Automatically switches icons based on system theme (Light/Dark).
- **Device Selection**: Choose specifically which microphone to control.

## Installation

### Prerequisites
- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (Recommended for dependency management)

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/madbeat14/MicMute.git
    cd MicMute
    ```

2.  **Install dependencies:**
    Using `uv` (Fastest & Recommended):
    ```bash
    uv sync
    ```
    
    *Or using standard pip:*
    ```bash
    pip install -e .
    ```

## Usage

### Running from Source
To run the application directly without building:

Using `uv`:
```bash
uv run python run.py
```

*Or with standard python:*
```bash
python run.py
```

### Building the Executable
To create a standalone `.exe` file:

```bash
uv run python build_exe.py
```
The executable will be generated in the `dist/` folder as `MicMute.exe`.

## Project Structure
- `src/MicMute`: Source code package.
- `run.py`: Entry point for running from source.
- `build_exe.py`: Script to build the standalone executable.
