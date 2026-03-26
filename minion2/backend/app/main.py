from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import uuid
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional

from .storage import Storage
from .skill_parser import parse_skill, Skill
from .orchestrator import Orchestrator

# ── Suppress noisy polling access logs ────────────────────────────────────────
# GET /api/logs/<sid> and /api/status/<sid> are polled every second by the
# frontend. Filter them from uvicorn.access; all other routes still log normally.
class _SuppressPollingLogs(logging.Filter):
    _QUIET_PATHS = ("/api/logs/", "/api/status/")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(p in msg for p in self._QUIET_PATHS)

logging.getLogger("uvicorn.access").addFilter(_SuppressPollingLogs())
# ──────────────────────────────────────────────────────────────────────────────


# Global Hub State
class Hub:
    def __init__(self):
        self.active_logs: Dict[str, List[str]] = {}
        self.status: Dict[str, str] = {}
        self.db: Storage = None
        self.orchestrator: Orchestrator = None

hub = Hub()
app = FastAPI(title="Minion 2.0 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # 🏛️ Minion 2.0 Persistence Protocol (High-Fidelity)
    # Linked to Local Discovery Hub where your mission history resides
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///minion_memory.db")
    print(f"📡 Syncing with Persistence Node: {db_url}...")
    hub.db = Storage(db_url)
    await hub.db.init()
    print("🏛️ Persistence synchronized. Hub is open for directives.")
    
    # 🏛️ Minion 2.0 Independence Discovery
    llm_url = os.getenv("LLM_URL", "http://localhost:11434")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # minion2/backend/
    hub.orchestrator = Orchestrator(llm_url, "qwen3.5:35b", hub.db, project_root)
    await hub.orchestrator.init()
    
    # Ready Signal for Dashboard Telemetry
    print(f"🚀 Minion 2.0 Web Hub Ready on Port 8001")
    print(f"🏛️  Independence Upgrade: Python Native Logic Online.")

@app.delete("/api/cache")
async def clear_cache():
    await hub.db.clear_cache()
    return {"status": "ok"}

@app.get("/api/history")
async def get_history():
    res = await hub.db.get_history()
    return json.loads(json.dumps(res, default=str))

# 🏛️ Synaptic Deployment Registry: Track active background reasoning tasks
active_tasks: Dict[str, asyncio.Task] = {}

def cancel_existing_task(sid: str):
    if sid in active_tasks:
        print(f"🛑 [HUB] Terminating orphaned task for session: {sid}")
        active_tasks[sid].cancel()
        del active_tasks[sid]

@app.get("/api/skills")
async def get_skills():
    # Use the localized 'skills/' directory within minion2/backend
    skill_dir = "skills"
    if not os.path.exists(skill_dir): return {}
    skills = {}
    for f in os.listdir(skill_dir):
        if f.endswith(".md"):
            try:
                s = parse_skill(os.path.join(skill_dir, f))
                skills[f.replace(".md", "")] = [p.name for p in s.phases]
            except Exception: continue
    return skills

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    task = data.get("task", "")
    sid = data.get("sessionId", f"session-{uuid.uuid4().hex[:8]}")
    model = data.get("model", "qwen3.5:35b")
    phases = data.get("phases", "").split(",") if data.get("phases") else None
    skill_type = data.get("skill", "research")
    
    # 🏛️ Neural Deployment Sync: Cancel any existing threads for this session
    # to prevent context-bloat and 'Ghost Reasoning' loops.
    cancel_existing_task(sid)
    
    # Prepare Mission Logs (In-Memory Buffer)
    hub.active_logs[sid] = [f"🚀 Mission Initiated: {sid}"]
    hub.status[sid] = "running"
    
    # 🏛️ High-Fidelity Task Spawning: Registry-bound background task
    t = asyncio.create_task(run_mission(sid, task, skill_type, model, phases))
    active_tasks[sid] = t
    
    return {"id": sid, "status": "started"}

async def run_mission(sid: str, task: str, skill_type: str, model: str, phases: List[str]):
    print(f"🚀 [HUB] Background Task Spawned for Session: {sid}")
    start_time = time.time()
    try:
        print(f"📡 [HUB] Syncing Mission Start to Database ({sid})...")
        await hub.db.record_start(sid, task, model, skill_type)
        print(f"✅ [HUB] Database Synced for {sid}.")
        
        # 📂 Blueprint Extraction
        skill_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills", f"{skill_type}.md")
        skill = parse_skill(skill_path)
        hub.active_logs[sid].append(f"🧠 Parsing skill: {skill_type}...")
        
        def log_cb(msg): 
            hub.active_logs[sid].append(msg)
            print(f"[{sid}] {msg}")

        res = await hub.orchestrator.run(skill, task, sid, phases, on_status=log_cb)
        hub.active_logs[sid].append(f"✅ Mission Complete: {res if res else 'Report Manifested'}")
        hub.status[sid] = "done"
        
        # ✅ FIX P0: record_end so sessions are no longer stuck as "running"
        duration_ms = int((time.time() - start_time) * 1000)
        await hub.db.record_end(sid, duration_ms, "success")
        
        
        # ✅ Parity Fix: If the agent manifested a full report file, prioritize archiving that long-form deliverable 
        # instead of the brief "PHASE_COMPLETE: Report written" confirmation text.
        final_report = res
        try:
            # Look at all dynamically named .md or .txt files generated by this specific session
            session_files = hub.orchestrator.written_reports.pop(sid, {})
            if session_files:
                # Rank files: prefer 'report' in name, fallback to largest file by character count
                best_match = None
                max_score = -1
                
                for path, content in session_files.items():
                    score = len(content)
                    if "report" in path.lower():
                        score += 1000000  # heavy priority to explicit report naming
                    
                    if score > max_score:
                        max_score = score
                        best_match = (path, content)
                
                if best_match:
                    path, content = best_match
                    hub.active_logs[sid].append(f"📑 [History] Dynamically detected long-form generated report at '{path}'. Archiving full deliverable...")
                    final_report = content
        except Exception as e:
            hub.active_logs[sid].append(f"⚠️ [History] Report extraction fault: {e}")

        hub.active_logs[sid].append(f"📡 Persisting final result to hub...")
        await hub.db.record_report(sid, task, final_report)
        hub.active_logs[sid].append(f"FINAL REPORT: \n{final_report}")
        hub.active_logs[sid].append(f"✅ Mission Complete: Intelligence Manifested.")
        
    except Exception as e:
        hub.active_logs[sid].append(f"❌ Critical Fault: {str(e)}")
        hub.status[sid] = "failed"
        # ✅ FIX P0: Also record failure so it's not stuck as "running"
        duration_ms = int((time.time() - start_time) * 1000)
        await hub.db.record_end(sid, duration_ms, "failure")

@app.get("/api/logs/{sid}")
async def get_logs(sid: str):
    return hub.active_logs.get(sid, [f"⚠️ Session {sid} not active or cleared."])

@app.get("/api/memories")
async def get_memories():
    return await hub.db.get_memories()

@app.get("/api/turns/{sid}")
async def get_turns(sid: str):
    res = await hub.db.get_turns(sid)
    return json.loads(json.dumps(res, default=str))

@app.get("/api/report/{sid}")
async def get_report(sid: str):
    res = await hub.db.get_report(sid)
    if not res: return JSONResponse(status_code=404, content={"error": "Not found"})
    return json.loads(json.dumps(res, default=str))

@app.get("/api/reports")
async def get_all_reports():
    res = await hub.db.get_all_reports()
    return json.loads(json.dumps(res, default=str))

@app.delete("/api/sessions/{sid}")
async def delete_session(sid: str):
    await hub.db.delete_session(sid)
    if sid in hub.active_logs: del hub.active_logs[sid]
    return {"status": "ok"}

# ✅ FIX P1: /api/vote — applies user feedback for DB-driven routing learning
@app.post("/api/vote/{sid}")
async def vote(sid: str, request: Request):
    data = await request.json()
    feedback = data.get("feedback", 0)  # Expect +1 or -1
    await hub.db.record_feedback(sid, feedback)
    return {"status": "ok", "session": sid, "feedback": feedback}

# ✅ FIX P1: /api/report-latest — read raw report file from disk (mirrors web-server.ts)
@app.get("/api/report-latest")
async def get_latest_report():
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "research_report.txt")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return f.read()
    return JSONResponse(status_code=404, content={"error": "No report file generated yet."})

# ✅ FIX P1: /api/memories/<sid> — per-session memory view (mirrors web-server.ts)
@app.get("/api/memories/{sid}")
async def get_session_memories(sid: str):
    res = await hub.db.get_memories(sid)
    return json.loads(json.dumps(res, default=str))

@app.get("/api/status/{sid}")
async def get_status(sid: str):
    return {"status": hub.status.get(sid, "unknown")}

# 🌍 Unified Frontend Distribution (Minion 2.0 Unified)
# In Docker, we host both the API and the static React files on a single port (3015)
frontend_dir = os.getenv("FRONTEND_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend-dist"))
if os.path.exists(frontend_dir):
    print(f"🌍 Unified Hub: Mounting Frontend Node from: {frontend_dir}")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
else:
    print("⚠️  Frontend assets not found. API mode ONLY. (Expected in Docker)")

