import PyInstaller.__main__
import os

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
ENTRY_POINT = os.path.join(BASE_DIR, "run.py")
ASSETS_SRC = os.path.join(SRC_DIR, "MicMute", "assets")
ASSETS_DEST = os.path.join("MicMute", "assets")

# PyInstaller arguments
args = [
    ENTRY_POINT,
    '--name=MicMute',
    '--onefile',
    '--windowed',  # Hide console
    '--noconfirm',
    '--clean',
    f'--paths={SRC_DIR}',
    f'--add-data={ASSETS_SRC}{os.pathsep}{ASSETS_DEST}',
    '--hidden-import=PySide6',
    '--hidden-import=pycaw',
]

print(f"Building EXE with args: {args}")
PyInstaller.__main__.run(args)
