# -*- mode: python ; coding: utf-8 -*-
# Freezes the model-context server into one km-mcp binary in dist/.
#   pyinstaller --noconfirm --clean km-mcp.spec
import os

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('mcp.server')
hiddenimports += collect_submodules('mcp.shared')
hiddenimports += collect_submodules('mcp.types')
hiddenimports += collect_submodules('mcp.os')
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('httpx')


a = Analysis(
    [os.path.join(SPECPATH, 'app', 'entrypoints', 'local.py')],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['mcp.cli', 'typer'],
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
    name='km-mcp',
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
