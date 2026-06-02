"""Convenience launcher for the AlphaAgent backend API.

Run with:
    uv run python main.py

Equivalent to the installed `alphaagent-api` script. Starts uvicorn on
127.0.0.1:8000 with auto-reload (see alphaagent/api/main.py:run).

Needs the `api` extra (and `data` for the analysis endpoints). If a bare
`uv run` ever strips them, bake them into the venv once:
    uv sync --extra api --extra data
or pass them inline:
    uv run --extra api --extra data python main.py
"""

from alphaagent.api.main import run

if __name__ == "__main__":
    run()
