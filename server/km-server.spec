# -*- mode: python ; coding: utf-8 -*-
# Freezes the engine into one km-server binary in dist/.
# The caller names the knowledge-model folder to bundle:
#   pyinstaller --noconfirm --clean km-server.spec -- --knowledge-model-dir <folder>
import argparse
import os

from PyInstaller.utils.hooks import collect_submodules

parser = argparse.ArgumentParser(prog='km-server.spec')
parser.add_argument('--knowledge-model-dir', required=True)
options = parser.parse_args()

hiddenimports = []
hiddenimports += collect_submodules('uvicorn')


a = Analysis(
    [os.path.join(SPECPATH, 'app', 'entrypoints', 'desktop.py')],
    pathex=[],
    binaries=[],
    datas=[(os.path.abspath(options.knowledge_model_dir), 'knowledge-model')],
    hiddenimports=hiddenimports,
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
    name='km-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)
