import subprocess
import json
import asyncio
import os
from typing import List, Dict, Any, Optional

class MCPClient:
    """
    🏛️ Minion 2.0 MCP Bridge:
    A high-fidelity communication Hub that connects the agent to external tool repositories 
    (like filesystem-mcp, terminal-mcp, etc.) via the standard MCP protocol.
    """
    
    def __init__(self, command: str, args: List[str], cwd: str = ".", env: Dict = {}):
        self.command = command
        self.args = args
        self.cwd = cwd
        self.env = {**os.environ, **env}
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0

    async def start(self):
        """
        🚀 Synaptic Ignition: Launching external MCP server process.
        """
        self.process = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
            env=self.env
        )
        print(f"📡 [MCP BRIDGE] Connected to External Host: {self.command} {' '.join(self.args)}...")
        
        # 🤝 Protocol HandshakeTurn
        # Initializing the server can be automated here if needed (v1 used listTools turn as discovery)

    async def list_tools(self) -> List[Dict]:
        """
        📂 Tool Discovery Protocol: 
        Retrieves the catalog of mission-ready tools from the external server.
        """
        if not self.process: await self.start()
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": self._get_next_id()
        }
        
        response = await self._send_request(request)
        return response.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, args: Dict) -> Any:
        """
        🛠️ Directive Dispatch Node: 
        Executes a specific tool command on the external server.
        """
        if not self.process: await self.start()
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": args
            },
            "id": self._get_next_id()
        }
        
        response = await self._send_request(request)
        return response.get("result", {}).get("content", [])

    def _get_next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _send_request(self, request: Dict) -> Dict:
        """
        📡 Internal Synaptic Transport: 
        Communicates with the external process via STDIN/STDOUT JSON-RPC.
        """
        if not self.process or not self.process.stdin:
            return {"error": "Process NOT manifested."}

        # 📠 Encode & Transmit Directive
        msg = json.dumps(request) + "\n"
        self.process.stdin.write(msg.encode())
        await self.process.stdin.drain()

        # 👂 Await Intelligence Response
        line = await self.process.stdout.readline()
        if not line: return {"error": "Synaptic Fault. Connection Lost."}
        
        return json.loads(line.decode())

    async def stop(self):
        """
        🏛️ Neutral Closure: Terminating external MCP connection.
        """
        if self.process:
            self.process.terminate()
            await self.process.wait()
