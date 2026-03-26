import os
from typing import Dict, Any, List

# All relative paths are anchored to the minion2/backend directory (where uvicorn runs).
# This matches the original web-server.ts behaviour where files landed in the project root.
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # minion2/


def _resolve(path: str) -> str:
    """
    Resolve a (possibly relative) path to an absolute one under _BASE_DIR.
    Strips any accidental leading slash so 'research_report.txt' and
    '/research_report.txt' both land in the same place.
    """
    return os.path.join(_BASE_DIR, path.lstrip("/"))


def read_file_p(path: str) -> str:
    """Reads content from a filesystem path."""
    if not path or path.strip() in ["", ".", "/"]:
        return "❌ Read Fault: Path cannot be empty or root."
    try:
        full = _resolve(path)
        if not os.path.exists(full):
            return f"❌ Access Error: {path} not found (looked at {full})."
        with open(full, 'r', encoding='utf-8') as f:
            return f.read()[:50000]
    except Exception as e:
        return f"❌ Read Fault: {str(e)}"


def write_file_p(path: str, content: str) -> str:
    """Writes content to a filesystem path (safe directory creation)."""
    if not path or path.strip() in ["", ".", "/"]:
        return "❌ Write Fault: Path cannot be empty or root."
    try:
        full = _resolve(path)
        parent = os.path.dirname(full)
        # Guard: only call makedirs when there is an actual parent directory to create
        if parent and parent != full:
            os.makedirs(parent, exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ File written to: {full}"
    except Exception as e:
        return f"❌ Write Fault: {str(e)}"


def list_dir_p(path: str) -> str:
    """Lists contents of a directory node."""
    try:
        full = _resolve(path)
        if not os.path.isdir(full):
            return f"❌ Node Error: {path} is not a directory (looked at {full})."
        files = sorted(os.listdir(full))
        return "\n".join(files) if files else "(empty directory)"
    except Exception as e:
        return f"❌ Listing Fault: {str(e)}"
