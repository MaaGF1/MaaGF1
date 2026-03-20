# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

SPEC_DIR = Path(os.getcwd()).resolve()
AGENT_ROOT = SPEC_DIR.parent

if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

block_cipher = None

a = Analysis(
    [str(AGENT_ROOT / 'main.py')], 
    pathex=[str(AGENT_ROOT)],
    binaries=[],
    datas=[
        (str(AGENT_ROOT / 'agent.conf'), '.'),
    ],
    hiddenimports=[
        'maa', 
        'maa.agent.agent_server',
        'maa.toolkit',
        'my_reco',
        'action',
        'server',
        'config',
        'utils',
        'utils.config',
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

pyd = []
for d in a.datas:
    if 'pyconfig' not in d[0]:
        pyd.append(d)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='maa_agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)