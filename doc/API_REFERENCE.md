# 🌐 Minion Hub 2.0 API Reference

The Minion 2.0 Hub provides a **RESTful Gateway** for dashboard interactions and programmatic mission control.

## 🚀 Authentication & Session
No authentication is enforced for local deployments. All missions are isolated by a `sessionId` (e.g., `session-1234`).

### 1. Unified Chat Directive (POST)
Starts a new research mission.
- **Endpoint**: `/api/chat`
- **Body**:
  ```json
  {
      "task": "research a developer named Shannon",
      "sessionId": "session-unique-id",
      "skill": "research",
      "phases": ["RECONNAISSANCE", "DEEP_OSINT"]
  }
  ```
- **Response**: `{"id": "session-unique-id", "status": "started"}`

---

### 2. Live Telemetry Polling (GET)
Returns the live execution logs for a session.
- **Endpoint**: `/api/logs/{sid}`
- **Response**: `["🚀 Mission Initiated", "[Step 1] Initializing Search..."]`

---

### 3. Mission Status (GET)
Checks if the agent is still reasoning or finished.
- **Endpoint**: `/api/status/{sid}`
- **Response**: `{"status": "running" | "done" | "failed"}`

---

### 4. Persistence History (GET)
Lists the 50 most recent missions.
- **Endpoint**: `/api/history`
- **Response**:
  ```json
  [
    {
      "id": "session-1234",
      "task_content": "Research Shannon",
      "status": "success",
      "duration_ms": 12500,
      "timestamp": "2024-03-26T15:00:00Z"
    }
  ]
  ```

---

### 5. Memory Archive (GET)
Returns all "Archived Intelligence" (key-value memories) across all sessions or for a specific one.
- **Endpoint**: `/api/memories` or `/api/memories/{sid}`
- **Response**: `[{"key": "email", "value": "shannon@example.com"}]`

---

### 6. Mission Result (GET)
Fetches the final report manifest for a completed mission.
- **Endpoint**: `/api/report/{sid}`
- **Response**: `{"session_id": "sid", "report_content": "FINAL REPORT: ..."}`

---

### 7. Global Intelligence Library (GET)
Returns a list of all saved research reports.
- **Endpoint**: `/api/reports`
- **Response**: `[{"session_id": "sid", "task": "research Shannon"}]`

## 📡 Port Strategy
- **Port 3015**: All API routes are pre-fixed with `/api/` and served concurrently with the React frontend in the unified Docker container.
