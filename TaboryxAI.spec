# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None
project_root = Path(os.getcwd()).resolve()

analysis = Analysis(
    [str(project_root / 'src' / 'app.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / 'web'), 'web')],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'SpeechRecognition',
        'pyaudiowpatch',
        'pyaudio',
    ],
    hookspath=[],
    hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name='TaboryxAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
)
