import subprocess
import os
import shlex
from typing import Dict, Any, List

class TerminalTool:
    """
    Python Native replacement for terminal-server.ts
    Executes shell commands with CWD statefulness.
    """
    def __init__(self, initial_cwd: str = "."):
        self.cwd = os.path.abspath(initial_cwd)

    async def shell_run(self, command: str) -> str:
        """Runs a shell command and returns formatted stdout/stderr."""
        try:
            # Basic CWD tracking in-process
            if command.startswith("cd "):
                target = command.split(" ", 1)[1]
                new_path = os.path.abspath(os.path.join(self.cwd, target))
                if os.path.isdir(new_path):
                    self.cwd = new_path
                    return f"📂 CWD UPDATED: {self.cwd}"
                return f"❌ Access Fault: {target} is not a directory."

            # Execute via subprocess
            # We use shell=True here to support pipes/redirects as the original did
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode().strip()
            error = stderr.decode().strip()
            
            if not output and not error:
                return "✅ Command completed successfully (No output)."
            
            # Combine output with professional formatting
            res = []
            if output: res.append(output)
            if error: res.append(f"⚠️ ERRORS:\n{error}")
            
            return "\n".join(res)[:10000] # Limit large outputs

        except Exception as e:
            return f"❌ Terminal Fault for '{command}': {str(e)}"

import asyncio
