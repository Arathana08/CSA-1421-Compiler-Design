"""One-Click Python Launcher for CompilerLab (VS Code Run Button or python run.py)."""
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


def main():
    print("=" * 54)
    print("  CompilerLab - Starting Backend & Frontend...")
    print("=" * 54)

    # Ensure Flask & Flask-CORS are installed
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(BACKEND_DIR / "requirements.txt")],
        check=False,
    )

    # Start Flask backend
    backend_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(BACKEND_DIR),
    )

    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Installing frontend packages (first run only)...")
        subprocess.run([npm_cmd, "install"], cwd=str(FRONTEND_DIR), check=True)

    # Start Vite frontend
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    time.sleep(2.5)
    url = "http://localhost:5173"
    print(f"Opening {url} in your browser...")
    webbrowser.open(url)
    print("Press Ctrl+C in this terminal to stop both servers.")

    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping servers...")
        frontend_proc.terminate()
        backend_proc.terminate()


if __name__ == "__main__":
    main()
