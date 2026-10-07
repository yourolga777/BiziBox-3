# -*- mode: python ; coding: utf-8 -*-
import os
import sys

sys.setrecursionlimit(5000)

FRONTEND_DIST = os.path.abspath(os.path.join("..", "frontend", "dist"))

block_cipher = None

a = Analysis(
    ['run_portable.py'],
    pathex=[],
    binaries=[],
    datas=[
        (FRONTEND_DIST, "frontend"),
        ("alembic.ini", "."),
        ("migrations", "migrations"),
    ],
    hiddenimports=[
        # FastAPI / uvicorn
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "pydantic",
        "pydantic.deprecated.decorator",
        # SQLAlchemy
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
        "aiosqlite",
        # Pyrogram
        "pyrogram",
        "pyrogram.client",
        "pyrogram.session",
        "pyrogram.connection",
        "pyrogram.connection.transport",
        "pyrogram.connection.transport.tcp",
        "pyrogram.connection.transport.tcp.tcp_abridged",
        "pyrogram.crypto",
        "pyrogram.crypto.aes",
        "pyrogram.crypto.mtproto",
        # Email
        "aiosmtplib",
        "email",
        "email.mime",
        "email.mime.text",
        "email.mime.multipart",
        "imaplib",
        # SOCKS5 proxy (Pyrogram optional transport)
        "socks",
        # Tray icon + browser launcher
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        # Other
        "cryptography",
        "cryptography.fernet",
        "asyncio",
        "multipart",
        "watchfiles",
        "watchfiles.watcher",
        # VK channel (REST via httpx)
        "httpx",
        "httpcore",
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BiziBox',
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
)
