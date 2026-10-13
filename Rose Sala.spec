# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['rose_sala.py'],
    pathex=['build-dependencies'],
    binaries=[('hosting-tools/cloudflared.exe', 'hosting-tools')],
    datas=[('hosting-tools/provenance.json', 'hosting-tools'), ('hosting-tools/LICENSE-cloudflared.txt', 'hosting-tools')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='Rose Sala',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Rose Sala',
)
