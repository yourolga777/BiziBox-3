#!/usr/bin/env python3
"""Cross-platform dev server launcher for BiziBox.

Usage:
    python scripts/dev.py

Starts backend (uvicorn) and frontend (vite) concurrently,
handles Ctrl+C gracefully by terminating both processes.
"""

import asyncio
import signal
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

BACKEND_CMD = [
    sys.executable, "-m", "uvicorn", "app.main:app",
    "--reload", "--port", "7910",
]
FRONTEND_CMD = ["npm", "run", "dev"]


async def check_dependencies() -> bool:
    """Check that required tools are available."""
    ok = True

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "--version",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        version = stdout.decode().strip()
        print(f"[OK] Python: {version}")
    except FileNotFoundError:
        print("[ERROR] Python not found.")
        ok = False

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", "--version",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        version = stdout.decode().strip()
        print(f"[OK] Node.js: {version}")
    except FileNotFoundError:
        print("[ERROR] Node.js not found. Install Node.js 18+.")
        ok = False

    if not ok:
        print("\n[ERROR] Please install missing dependencies and try again.")
        return False

    return True


async def run_process(
    name: str, cmd: list[str], cwd: Path,
) -> asyncio.subprocess.Process:
    print(f"[START] {name}: {' '.join(cmd)}")
    return await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )


async def stream_output(name: str, proc: asyncio.subprocess.Process) -> None:
    """Read and print output from a subprocess."""
    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        print(f"[{name}] {line.decode().rstrip()}")


async def main() -> None:
    if not await check_dependencies():
        sys.exit(1)

    print()
    print("=" * 50)
    print("  BiziBox — Dev Server")
    print("=" * 50)
    print()

    backend_proc = await run_process("backend", BACKEND_CMD, BACKEND_DIR)
    frontend_proc = await run_process("frontend", FRONTEND_CMD, FRONTEND_DIR)

    print()
    print("=" * 50)
    print("  Backend:  http://localhost:7910")
    print("  Frontend: http://localhost:5173")
    print("  API docs: http://localhost:7910/docs")
    print("=" * 50)
    print("  Press Ctrl+C to stop both servers.")
    print()

    async def cleanup() -> None:
        print("\n[INFO] Shutting down...")
        for name, proc in [("backend", backend_proc), ("frontend", frontend_proc)]:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                print(f"[OK] {name} stopped.")

    def signal_handler() -> None:
        asyncio.ensure_future(cleanup())

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass

    try:
        await asyncio.gather(
            stream_output("backend", backend_proc),
            stream_output("frontend", frontend_proc),
        )
    except asyncio.CancelledError:
        pass
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
