#!/usr/bin/env python
"""
Developer Build Script - For maintainer use only.
Upgrades all dependencies to latest, syncs, locks, and builds.

Usage: python dev_build.py
"""
import subprocess
import sys
import os

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

def run_cmd(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*50}")
    print(f"→ {description}")
    print(f"{'='*50}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"✗ FAILED: {description}")
        sys.exit(1)
    print(f"✓ {description}")
    return result

def check_uv():
    """Check if uv is available, try to install if not."""
    print("\n→ Checking for uv...")
    
    # Try running uv via python module
    result = subprocess.run(
        [sys.executable, "-m", "uv", "--version"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✓ uv found: {result.stdout.strip()}")
        return True
    
    # Try installing uv
    print("⚠ uv not found, attempting to install...")
    install_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "uv"],
        capture_output=True
    )
    
    if install_result.returncode == 0:
        print("✓ uv installed successfully")
        return True
    
    print("✗ Failed to install uv. Please install manually: pip install uv")
    sys.exit(1)

def main():
    print("""
╔══════════════════════════════════════════════════╗
║          MicMute Developer Build Script          ║
║      Upgrade → Sync → Lock → Generate → Build    ║
╚══════════════════════════════════════════════════╝
    """)
    
    # Check uv
    check_uv()
    
    # Use python -m uv for reliability
    uv_cmd = f'"{sys.executable}" -m uv'
    
    # Step 1: Upgrade dependencies
    run_cmd(f'{uv_cmd} sync --upgrade', "Upgrading dependencies")
    
    # Step 2: Lock dependencies
    run_cmd(f'{uv_cmd} lock', "Locking dependencies")
    
    # Step 3: Generate spec file
    run_cmd(f'"{sys.executable}" generate_spec.py', "Generating spec file")
    
    # Step 4: Build executable
    run_cmd(f'"{sys.executable}" build_exe.py', "Building executable")
    
    print(f"""
╔══════════════════════════════════════════════════╗
║              BUILD COMPLETE! ✓                   ║
╠══════════════════════════════════════════════════╣
║  Output: dist/MicMute.exe                        ║
╚══════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    main()
