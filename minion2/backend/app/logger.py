import os
from datetime import datetime


class SessionLogger:
    """
    Ports logger.ts → Python.
    Writes every LLM turn (prompt + response + latency) to a persistent
    timestamped log file at logs/<session_id>.log for offline debugging.
    """

    def __init__(self, project_root: str, session_id: str):
        log_dir = os.path.join(project_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, f"{session_id}.log")

    def log_turn(self, prompt: str, response: str, duration_ms: int, model: str = ""):
        time_str = datetime.now().strftime("%H:%M:%S")
        entry = (
            f"\n[{time_str}] (Model: {model} | Latency: {duration_ms}ms)\n"
            f"PROMPT: {prompt}\n"
            f"RESPONSE: {response}\n"
            f"{'-' * 80}\n"
        )
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            print(f"⚠️ [Logger] Could not write turn: {str(e)}")

    def log_event(self, message: str):
        """Log a free-form event (phase start, tool call, etc.)."""
        time_str = datetime.now().strftime("%H:%M:%S")
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time_str}] EVENT: {message}\n")
        except Exception:
            pass
