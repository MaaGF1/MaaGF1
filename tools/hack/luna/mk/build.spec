# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

SPEC_DIR = Path(os.getcwd()).resolve()
LUNA_ROOT = SPEC_DIR.parent
SRC_DIR = LUNA_ROOT / 'src'

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

block_cipher = None

a = Analysis(
    [str(SRC_DIR / 'main.py')], 
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[
        (str(SRC_DIR / 'hook.js'), '.'),
    ],
    hiddenimports=[
        'frida',
        'tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Generate as directory (--onedir) instead of a single file for faster startup
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='luna',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Set to False to hide background CMD window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='luna'
)