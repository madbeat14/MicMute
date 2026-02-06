import PyInstaller.__main__
import os
import subprocess
import sys

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
ENTRY_POINT = os.path.join(BASE_DIR, "run.py")
ASSETS_SRC = os.path.join(SRC_DIR, "MicMute", "assets")
ASSETS_DEST = os.path.join("MicMute", "assets")
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")

# Generate spec file first
print("Generating spec file...")
spec_result = subprocess.run([sys.executable, "generate_spec.py"], cwd=BASE_DIR)
if spec_result.returncode != 0:
    print("ERROR: Failed to generate spec file")
    sys.exit(1)

# PyInstaller arguments
# We now use the .spec file as the source of truth
spec_file = os.path.join(BASE_DIR, "MicMute.spec")

args = [
    spec_file,
    '--noconfirm',
    '--clean',
    f'--distpath={DIST_DIR}',
    f'--workpath={BUILD_DIR}',
]

print(f"\nBuilding EXE using spec file: {spec_file}")
PyInstaller.__main__.run(args)
