"""Run the API server: python -m generador_sprites.api [--port PORT] [--reload]"""

import sys
from pathlib import Path

# Ensure the parent directory is in sys.path so 'generador_sprites' is importable
# even when running from inside the project directory.
_project_parent = str(Path(__file__).resolve().parent.parent.parent)
if _project_parent not in sys.path:
    sys.path.insert(0, _project_parent)

import uvicorn


def main():
    port = 8000
    reload = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--reload":
            reload = True
            i += 1
        else:
            i += 1

    uvicorn.run("generador_sprites.api.app:app", host="0.0.0.0", port=port, reload=reload)


if __name__ == "__main__":
    main()
