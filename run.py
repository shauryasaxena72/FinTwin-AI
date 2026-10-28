"""Runner: starts backend (FastAPI) and frontend (Vite) with one command."""

import subprocess
import sys
import os
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
FINTWIN = os.path.join(ROOT, "fintwin")
FRONTEND = os.path.join(ROOT, "fintwin-frontend")

def main():
    # Start backend
    backend = subprocess.Popen(
        [sys.executable, "api.py"],
        cwd=FINTWIN,
    )
    print("Backend started on http://localhost:8000")
    time.sleep(2)

    # Start frontend
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND,
        shell=True,
    )
    print("Frontend started on http://localhost:5173/FinTwin-AI/")
    print("Press Ctrl+C to stop both.")

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()
        print("Stopped.")

if __name__ == "__main__":
    main()
