# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['adb_auto_player/main.py'],
    pathex=['adb_auto_player'],
    binaries=[],
    datas=[
        ('pyproject.toml', '.')
    ],
    hiddenimports=[
        'adb_auto_player.plugin',
        'bottle_websocket',
        '_socket',
        'unicodedata',
        'eel'
    ],
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
    name='AdbAutoPlayer',
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
    icon='koko.ico',
)
