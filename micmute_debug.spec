# -*- mode: python ; coding: utf-8 -*-
# Debug version with console enabled

from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

import MicMute

a = Analysis(
    [r'C:\Users\papop\Desktop\TaskScheduler\MicMute\run.py'],
    pathex=[r'C:\Users\papop\Desktop\TaskScheduler\MicMute\src'],
    binaries=[],
    datas=[(r'C:\Users\papop\Desktop\TaskScheduler\MicMute\src\MicMute\assets', 'MicMute\assets')],
    hiddenimports=[
        'PySide6',
        'comtypes',
        'pycaw',
        'winsound',
        'MicMute._version',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Windows version info
vs_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(2, 13, 10, 0),
        prodvers=(2, 13, 10, 0),
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    '040904B0',
                    [
                        StringStruct('CompanyName', 'madbeat14'),
                        StringStruct('FileDescription', 'MicMute - Microphone Mute Toggle'),
                        StringStruct('FileVersion', '2.13.10.dev0+g7c94a2202.d20260206'),
                        StringStruct('InternalName', 'MicMute'),
                        StringStruct('LegalCopyright', 'Copyright (c) 2024 madbeat14'),
                        StringStruct('OriginalFilename', 'MicMute.exe'),
                        StringStruct('ProductName', 'MicMute'),
                        StringStruct('ProductVersion', '2.13.10.dev0+g7c94a2202.d20260206'),
                    ]
                )
            ]
        ),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])
    ]
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MicMute_Debug',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # DEBUG: Enable console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=vs_info,
)
