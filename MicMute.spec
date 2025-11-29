# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['c:\\Users\\papop\\Desktop\\TaskScheduler\\MicMute\\run.py'],
    pathex=['c:\\Users\\papop\\Desktop\\TaskScheduler\\MicMute\\src'],
    binaries=[],
    datas=[('c:\\Users\\papop\\Desktop\\TaskScheduler\\MicMute\\src\\MicMute\\assets', 'MicMute\\assets')],
    hiddenimports=['PySide6', 'comtypes', 'pycaw', 'winsound'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MicMute',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
