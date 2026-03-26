import asyncio
from datetime import datetime
import json
import os
import re
import uuid
import time
import httpx
from typing import List, Dict, Any, Optional, Callable, Tuple
from .skill_parser import Skill, SkillPhase, parse_skill
from .storage import Storage
from .logger import SessionLogger

# Native Tool Imports
from .tools.fetch_tool import fetch_url
from .tools.browser_tool import BrowserTool
from .tools.memory_tool import remember_memory, recall_memory, forget_memory, list_memories
from .tools.file_tool import read_file_p, write_file_p, list_dir_p
from .tools.validator_tool import validate_json
from .tools.calc_tool import calculate
from .tools.search_tool import web_search_p
from .tools.terminal_tool import TerminalTool
from .router import ModelRouter

def _hash_messages(messages: List[Dict]) -> str:
    """Deterministic hash of chat history matching TS llm-cache.ts"""
    normalized = "|".join([f"{m.get('role', '').strip().lower()}:{m.get('content', '').strip()}" for m in messages])
    import hashlib
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

class Orchestrator:
    MAX_SEARCHES_PER_PHASE = 3  # Max web_search calls per phase (resets each phase)
    SEARCH_TOOLS = {
        "web_search", "search_engine", "search", "google_search", "google",
        "search_web", "search_duckduckgo", "search_engine_query"
    }

    def __init__(self, llm_url: str, model: str, storage: Storage, project_root: str = "."):
        self.llm_url = llm_url
        self.model = model
        self.storage = storage
        self.router = ModelRouter(storage)
        self.project_root = project_root
        self.browser = BrowserTool(storage)
        self.cwd = os.getcwd()
        self.terminal = TerminalTool(self.cwd)
        # Per-phase search counter — reset at start of each phase
        self._phase_search_count: int = 0
        # Tracks generated files per session to catch dynamically named reports
        self.written_reports: Dict[str, Dict[str, str]] = {}

    async def init(self):
        """Initializes high-fidelity tool bridges."""
        print("🏛️ Minion 2.0 Native Logic Engine Online.")

    # -----------------------------------------------------------------
    # Tool Dispatcher
    # -----------------------------------------------------------------
    async def call_native_tool(self, name: str, args: Dict[str, Any], sid: str) -> str:
        """Dispatches directives to the appropriate Python-native discovery engine."""
        try:
            if name == "fetch":
                return await fetch_url(args.get("url", ""))
            elif name in ["goto", "scrape"]:
                url = args.get("url", "")
                if not url or not url.startswith("http"):
                    return "❌ Fault: You must provide a valid starting URL (e.g. https://...). Ensure you extracted a URL from the previous search logic."
                return await self.browser.goto_and_scrape(url)
            elif name in ["remember", "remember_memory"]:
                return await remember_memory(self.storage, sid, args.get("key"), args.get("value"))
            elif name in ["recall", "recall_memory"]:
                return await recall_memory(self.storage, sid, args.get("key"))
            elif name in ["forget", "forget_memory"]:
                return await forget_memory(self.storage, sid, args.get("key"))
            elif name == "list_memories":
                return await list_memories(self.storage, sid)
            elif name in ["read_file", "write_file"]:
                path = args.get("path", "").lstrip("/")
                if not path:
                    return f"❌ Fault: '{name}' requires a valid 'path' argument in the JSON payload."
                
                if name == "read_file": 
                    return read_file_p(path)
                
                content = args.get("content", "")
                if not content:
                    return "❌ Fault: 'write_file' requires a 'content' argument containing the text to write."
                    
                if path.lower().endswith((".txt", ".md")):
                    self.written_reports.setdefault(sid, {})[path] = content
                    
                return write_file_p(path, content)
            elif name == "list_dir":
                return list_dir_p(args.get("path", ".").lstrip("/"))
            elif name in ["calculate", "add"]:
                op = f"{args.get('a', '')} + {args.get('b', '')}" if 'a' in args else args.get("operation", "")
                return calculate(op)
            elif name == "scrape_text":
                return await self.browser.scrape_text()
            elif name == "json_validation":
                return validate_json(args.get("json", args.get("content", "")))
            elif name in self.SEARCH_TOOLS:
                # ── Per-Phase Search Budget ─────────────────────────────
                count = self._phase_search_count
                if count >= self.MAX_SEARCHES_PER_PHASE:
                    msg = (
                        f"🚫 [SEARCH LIMIT] You have used all {self.MAX_SEARCHES_PER_PHASE} searches for this phase. "
                        f"Do NOT call web_search again in this phase. "
                        f"Use 'goto' to visit a specific URL, or output PHASE_COMPLETE with what you have."
                    )
                    print(f"🚫 [SEARCH] Phase limit hit ({count}/{self.MAX_SEARCHES_PER_PHASE})")
                    return msg
                self._phase_search_count += 1
                remaining = self.MAX_SEARCHES_PER_PHASE - self._phase_search_count
                q_val = args.get('query') or args.get('queries') or args.get('q', '')
                final_q = " ".join(q_val) if isinstance(q_val, list) else q_val
                print(f"🔍 [SEARCH] #{self._phase_search_count}/{self.MAX_SEARCHES_PER_PHASE}: {final_q[:80]}")
                result = await self.browser.deep_search(final_q)
                if remaining > 0:
                    result += f"\n\n⚠️ Search {self._phase_search_count}/{self.MAX_SEARCHES_PER_PHASE} used this phase ({remaining} left)."
                else:
                    result += f"\n\n🚫 Phase search limit reached ({self.MAX_SEARCHES_PER_PHASE}/{self.MAX_SEARCHES_PER_PHASE}). Use 'goto' for specific URLs or output PHASE_COMPLETE."
                return result
            elif name == "shell_run":
                cmd = args.get("command", "")
                if not cmd:
                    return "❌ Fault: command is required."
                return await self.terminal.shell_run(cmd)
            elif name == "spawn_minion":
                skill_name = args.get("skill", "")
                sub_task = args.get("task", "")
                if not skill_name or not sub_task:
                    return "❌ Fault: skill and task are required."
                try:
                    # Recursive Sub-Agent Call
                    sub_skill = parse_skill(skill_name, os.path.join(self.project_root, "minion2", "skills"))
                    if not sub_skill:
                        sub_skill = parse_skill(skill_name, os.path.join(self.project_root, "backend", "skills"))
                    if not sub_skill:
                        return f"❌ Fault: Sub-skill '{skill_name}' not found."
                    
                    sub_sid = f"sub-{sid}-{int(time.time())}"
                    sub_orch = Orchestrator(self.llm_url, self.model, self.storage, self.project_root)
                    print(f"🔄 [SUB-AGENT] Spawning '{skill_name}' for task: {sub_task[:80]}...")
                    sub_result = await sub_orch.run(sub_skill, sub_task, sub_sid)
                    return f"✅ Sub-Agent [{skill_name}] Finished.\nResult:\n{sub_result}"
                except Exception as e:
                    return f"❌ Sub-Agent Fault: {str(e)}"

            return f"❌ Native Tool Error: {name} not found in the 2.0 Toolkit."
        except Exception as e:
            return f"❌ Directive Fault in {name}: {str(e)}"

    # -----------------------------------------------------------------
    # ✅ FIX P0: Multi-tool-call extraction (brace depth matching)
    # Ports extractToolCalls() from orchestrator.ts
    # -----------------------------------------------------------------
    def extract_tool_calls(self, text: str) -> List[Tuple[str, str]]:
        """
        Finds ALL TOOL: name {...} calls in a single LLM response.
        Uses brace-depth matching and skips parsed blocks to avoid collision.
        Returns a list of (tool_name, args_json_string) tuples.
        """
        results = []
        pattern = re.compile(r"TOOL:\s*(\w+)")
        ptr = 0
        
        while True:
            match = pattern.search(text, ptr)
            if not match:
                break
                
            tool_name = match.group(1)
            ptr = match.end()
            
            # Find starting brace
            json_start = text.find('{', ptr)
            if json_start == -1:
                results.append((tool_name, "{}"))
                continue
                
            # Brace depth matching
            depth = 0
            json_end = -1
            for i in range(json_start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        json_end = i + 1
                        break
            
            if json_end != -1:
                # Successfully parsed a tool call. 
                # CRITICAL: Jump the pointer PAST the JSON to avoid double-parsing 'TOOL:' inside values.
                results.append((tool_name, text[json_start:json_end]))
                ptr = json_end
            else:
                # Malformed JSON, append empty and move on
                results.append((tool_name, "{}"))
        
        return results

    def get_tool_manual(self):
        tools_path = os.path.join(os.path.dirname(__file__), "tools")
        manual_lines = ["🏛️ MINION 2.0 TOOLKIT CATALOG:"]
        
        manual_lines.append("1. web_search {\"query\": \"string\"}: Engage DuckDuckGo/Google OSINT Matrix.")
        manual_lines.append("2. goto {\"url\": \"string\"}: Navigate directly to a target domain for manual scraping.")
        manual_lines.append("3. scrape_text {}: Extract text content from the current open browser landing page.")
        
        if os.path.exists(tools_path):
            count = 4
            for f in sorted(os.listdir(tools_path)):
                if f.endswith("_tool.py"):
                    t_name = f.replace("_tool.py", "")
                    if t_name == "memory":
                        manual_lines.append(f"{count}. remember_memory {{\"key\": \"string\", \"value\": \"string\"}}: Persist intelligence.")
                        manual_lines.append(f"{count+1}. recall_memory {{\"query\": \"string\"}}: Search context.")
                        manual_lines.append(f"{count+2}. forget_memory {{\"key\": \"string\"}}: Delete an incorrect or stale memory.")
                        manual_lines.append(f"{count+3}. list_memories {{}}: List all stored memories with IDs.")
                        count += 4
                    elif t_name == "file":
                        manual_lines.append(f"{count}. read_file {{\"path\": \"string\"}}: Access artifacts.")
                        manual_lines.append(f"{count+1}. write_file {{\"path\": \"string\", \"content\": \"string\"}}: Manifest reports.")
                        count += 2
                    elif t_name == "calc":
                        manual_lines.append(f"{count}. calculate {{\"expr\": \"string\"}}: Perform arithmetic.")
                        count += 1
                    elif t_name == "validator":
                        manual_lines.append(f"{count}. json_validation {{\"content\": \"string\"}}: Verify data integrity.")
                        count += 1
                    elif t_name == "terminal":
                        manual_lines.append(f"{count}. shell_run {{\"command\": \"string\"}}: Execute shell operations system-side.")
                        count += 1
                    elif t_name == "fetch":
                        manual_lines.append(f"{count}. fetch {{\"url\": \"string\"}}: Direct non-render HTTP fetch.")
                        count += 1

        # Add missing tools not mapped 1:1 by file name
        manual_lines.append(f"{count}. list_dir {{\"path\": \"string\"}}: Examine directory tree structure.")
        count += 1
        manual_lines.append(f"{count}. spawn_minion {{\"skill\": \"string\", \"task\": \"string\"}}: Spawn a sub-agent for deep, recursive delegation.")
        count += 1
        
        return (
            "\n".join(manual_lines)
            + f"\n\n⚠️ SEARCH DISCIPLINE:\n"
            + f"  - Each phase allows up to {self.MAX_SEARCHES_PER_PHASE} web_search calls.\n"
            + "  - The Strategize phase must PLAN queries but NOT execute them — output PHASE_COMPLETE after planning.\n"
            + "  - Execute searches in the Search phase only.\n"
            + "  - After your search limit, use 'goto' + 'scrape_text' for specific URLs, or compile what you have.\n"
            + "\nUnified Response Format: Always use 'TOOL: tool_name {...args...}' for logic calls "
            + "and 'PHASE_COMPLETE: reason' when the instructions for the phase are 100% complete."
        )

    def get_system_prompt(self, skill: Skill, task: str):
        return f"""You are Minion 2.0, an AI research agent. 
CURRENT DATE: {datetime.now().strftime('%Y-%m-%d')}
ADOPT THIS PERSONA: {skill.persona}

You are performing the skill: {skill.name}.

{self.get_tool_manual()}

Follow the instructions for each phase precisely.
If you need to call a tool, output exactly: TOOL: tool_name {{JSON_ARGS}}
DO NOT output PHASE_COMPLETE in the same message as a TOOL: call.

STRATEGY:
1. GROUNDED: Do NOT hallucinate. When summarizing or reporting, use ONLY the information provided in the conversation history or tool results. If information is missing, clearly state that it was not found.
2. PERSISTENCE: At the start of a task, check your memory for relevant past experiences using 'recall_memory'.
3. LEARNING: At the end of a successful task, 'remember_memory' any key insights or fixes for future use.
4. CONCISE: Call tools as needed, observe their results in next turn, and once you have truly finished the instruction for that phase, ONLY then output: PHASE_COMPLETE: [Your summary]

MISSION DIRECTIVE: {task}
"""

    async def run(self, skill: Skill, task: str, sid: str, target_phases: List[str] = None, on_status: Optional[Callable[[str], None]] = None):
        # ✅ FIX P1: Create per-session logger (ports logger.ts)
        logger = SessionLogger(self.project_root, sid)
        logger.log_event(f"Mission started | Skill: {skill.name} | Task: {task[:100]}")

        # ✅ FIX P1: Shared history across phases (like original TS)
        history = [{"role": "system", "content": self.get_system_prompt(skill, task)}]
        
        # Hydration Recall
        mems = await self.storage.get_memories(sid)
        if mems:
            mem_text = "\n".join([f"• {m['key']}: {m['value']}" for m in mems])
            history.append({"role": "user", "content": f"KNOWLEDGE RECALLED FROM PREVIOUS PHASES:\n{mem_text}"})
            if on_status: on_status(f"🧠 Hydrating mission with {len(mems)} memories.")

        phases = skill.phases
        if on_status: on_status(f"🎯 Mission Plan: {len(phases)} phases identified in {skill.name}.")
        
        if target_phases:
            start_idx = next((i for i, p in enumerate(phases) if p.name == target_phases[0]), 0)
            phases = phases[start_idx:]
            if on_status: on_status(f"🚀 Selective Restart: Skipping to phase '{target_phases[0]}'.")

        for i, phase in enumerate(phases):
            if on_status: on_status(f"PHASE [{i+1}/{len(phases)}]: {phase.name} (Active)")
            logger.log_event(f"--- PHASE [{i+1}/{len(phases)}]: {phase.name} ---")
            
            # Reset per-phase search counter before each phase
            self._phase_search_count = 0
            
            # Pass shared history into run_phase (no isolation)
            last_ans = await self.run_phase(phase, task, sid, history, logger, on_status)
            
            # Carry forward phase summaries
            if "PHASE_COMPLETE" in last_ans:
                history.append({"role": "user", "content": f"PREVIOUS PHASE RESULT ({phase.name}): {last_ans}"})

        logger.log_event("Mission complete.")
        return history[-1]["content"] if history else "Mission complete."

    async def run_phase(self, phase: SkillPhase, task: str, sid: str, history: List[Dict], logger: SessionLogger, on_status: Optional[Callable[[str], None]] = None):
        history.append({"role": "user", "content": f"MISSION DIRECTIVE: {task}\nCURRENT PHASE: {phase.name}\nINSTRUCTIONS: {phase.instruction}"})
        
        active_model = await self.router.select_model(phase.instruction, sid)
        max_turns = 8  # Bump from 5 to 8 to match original's generosity

        if on_status: on_status(f"🧠 Phase Neural Alignment: Engaging {active_model}")

        for turn_num in range(1, max_turns + 1):
            if on_status: on_status(f"📡 turn {turn_num}/{max_turns}: Requesting Directive from {active_model}...")
            
            # Synaptic Window: System prompt + last 10 messages to prevent bloat
            current_context = history[:1] + history[-10:] if len(history) > 12 else history
            
            prompt_hash = _hash_messages(current_context)
            cached_ans = await self.storage.get_llm_cache(active_model, prompt_hash)
            
            if cached_ans:
                ans = cached_ans
                latency = 0
                logger.log_turn("(CACHE HIT) " + current_context[-1]["content"], ans, latency, active_model)
            else:
                # LLM Call with 3 retries
                ans = ""
                for attempt in range(3):
                    start_llm = time.time()
                    try:
                        async with httpx.AsyncClient(timeout=120.0) as client:
                            res = await client.post(f"{self.llm_url.rstrip('/')}/api/chat", json={
                                "model": active_model,
                                "messages": current_context,
                                "stream": False
                            })
                            res.raise_for_status()
                            ans = res.json()["message"]["content"]
                        latency = int((time.time() - start_llm) * 1000)
                        print(f"✅ [SUCCESS] turn {turn_num}: Received response in {latency}ms.")
                        # ✅ FIX P1: Write each turn to the session log file
                        prompt_text = current_context[-1]["content"] if current_context else ""
                        logger.log_turn(prompt_text, ans, latency, active_model)
                        
                        # Save to cache
                        await self.storage.set_llm_cache(active_model, prompt_hash, ans)
                        break
                    except Exception as e:
                        latency = int((time.time() - start_llm) * 1000)
                        print(f"⚠️ [WARN] turn {turn_num} (att {attempt+1}): Synaptic Fault: {str(e)}")
                        if attempt == 2:
                            ans = f"❌ [SYNAPTIC FAULT] LLM Communication error: {str(e)}"
                    await asyncio.sleep(1)

            history.append({"role": "assistant", "content": ans})
            if on_status: on_status(f"assistant: {ans[:200]}...")

            # Also persist the actual LLM turn to the DB for the dashboard parity
            prompt_text = current_context[-1]["content"] if current_context else ""
            await self.storage.record_turn(sid, active_model, prompt_text, ans, latency)

            # ✅ FIX P0: Multi-tool-call parsing (brace-depth matching, all calls per turn)
            tool_calls = self.extract_tool_calls(ans)
            if tool_calls:
                for (tname, targs_str) in tool_calls:
                    try:
                        targs = json.loads(targs_str)
                        if on_status: on_status(f"🛠️ [DIRECTIVE] EXEC {tname} {targs_str[:100]}")
                        logger.log_event(f"TOOL CALL: {tname} {targs_str[:100]}")

                        start_t = time.time()
                        result = await self.call_native_tool(tname, targs, sid)
                        t_latency = int((time.time() - start_t) * 1000)
                        
                        history.append({"role": "user", "content": f"TOOL RESULT [{tname}]: {result}"})
                        if on_status: on_status(f"📡 [DATA] {result[:200]}...")
                        logger.log_event(f"TOOL RESULT [{tname}]: {result[:200]}")
                    except json.JSONDecodeError as e:
                        err_msg = f"❌ [FORMAT FAULT] Invalid JSON for tool {tname}: {str(e)}"
                        history.append({"role": "user", "content": err_msg})
                        logger.log_event(err_msg)
                continue  # Always loop back after executing tools

            if "PHASE_COMPLETE:" in ans:
                msg = ans.split("PHASE_COMPLETE:")[1].strip()
                if on_status: on_status(f"✅ Phase Done: {phase.name} - {msg}")
                logger.log_event(f"PHASE_COMPLETE: {msg[:100]}")
                break

            # ✅ FIX P0: "Continue until Phase Complete" nudge — prevents silent stalls
            history.append({"role": "user", "content": "Continue until Phase Complete. If you have completed all required actions for this phase, output PHASE_COMPLETE: [summary]."})
            logger.log_event(f"turn {turn_num}: No tool call or PHASE_COMPLETE detected — nudging agent to continue.")

        else:
            # Loop exhausted without break
            if on_status: on_status(f"⚠️ Warning: Phase loop limit reached for {phase.name}")
            logger.log_event(f"⚠️ Phase loop limit ({max_turns}) reached for {phase.name}")

        return ans
