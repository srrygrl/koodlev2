# -*- mode: python ; coding: utf-8 -*-
#
# Spec do PyInstaller para o Koddle.
# Gera um único .exe (--onefile, --windowed) com a pasta ui/ embutida.
#
# Uso:
#   pyinstaller koddle.spec
#
# O executável final aparece em dist/Koddle.exe

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# O pacote winrt é compilado (extensões nativas) e carrega submódulos
# dinamicamente, então o PyInstaller não detecta tudo sozinho — precisamos
# forçar a coleta completa dele (e do webview, por segurança).
datas = []
binaries = []
hiddenimports = []

for pkg in ["winrt", "webview"]:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# Pasta com o HTML/CSS/JS da interface — precisa ir junto, fora do .py
datas += [("ui", "ui")]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Koddle",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # janela sem console (--windowed)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico" if __import__("os").path.exists("icon.ico") else None,
)
