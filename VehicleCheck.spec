# -*- mode: python ; coding: utf-8 -*-
import runpy
from pathlib import Path

from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)


PROJECT_ROOT = Path(SPECPATH).resolve()
APP_VERSION = runpy.run_path(str(PROJECT_ROOT / "version.py"))["APP_VERSION"]
version_parts = tuple(int(part) for part in APP_VERSION.split("."))
if len(version_parts) != 3:
    raise ValueError("APP_VERSION must use major.minor.patch format")
version_tuple = (*version_parts, 0)

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("ProductName", "VehicleCheck"),
                        StringStruct("FileDescription", "VehicleCheck"),
                        StringStruct("FileVersion", f"{APP_VERSION}.0"),
                        StringStruct("ProductVersion", APP_VERSION),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

datas = []
binaries = []
hiddenimports = []
tzdata = collect_all("tzdata")
datas += tzdata[0]
binaries += tzdata[1]
hiddenimports += tzdata[2]

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
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
    name=f"VehicleCheck-{APP_VERSION}",
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
    version=version_info,
)
