"""
Minimal reload-trigger server used by nodemon in dev.
Usage:
  Terminal 1: uvicorn app.main:app --reload
  Terminal 2: nodemon --watch app/static --exec "python frontend/dev-reload.py trigger"

The frontend, when served with DEV_RELOAD=1, polls /api/reload-check
once per second and reloads on a changed mtime.
"""
import os, sys, time

STAMP_PATH = os.path.join(os.path.dirname(__file__), ".reload-stamp")

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "trigger":
    with open(STAMP_PATH, "w") as f:
        f.write(str(time.time()))
    print(f"[dev-reload] {time.strftime('%H:%M:%S')} triggered")

