# 🚀 Minion Hub 2.0 Deployment Guide

The Minion 2.0 system is optimized for **Unified Deployment**, where the backend and frontend coexist in a high-performance environment. You can deploy locally or as a **Single-Port Container**.

## 🛠️ Unified Docker Deployment (Recommended)

This is the most stable and isolated way to run the Minion Hub. All assets are served on **Port 3015**.

### 1. Prerequisites
- Docker & Docker Compose installed.
- A running Postgres instance (local or remote).
- An LLM provider (Ollama or OpenAI).

### 2. Configuration
The system uses `devops/docker-compose.yml` and `devops/Dockerfile`. Update the environment variables in `docker-compose.yml`:
```yaml
environment:
  - DATABASE_URL=postgresql+psycopg://postgres:your_password@host.docker.internal/dao_db?options=-csearch_path%3Dminion
  - LLM_URL=http://host.docker.internal:11434
```
> [!TIP]
> Use `host.docker.internal` to let the container reach your host's Postgres or Ollama server.

### 3. Launching
From the project root:
```bash
docker-compose -f devops/docker-compose.yml up --build -d
```
The dashboard will be available at: **`http://localhost:3015`**.

---

## 💻 Local Development Setup

To run the components individually for development purposes:

### 1. Backend (Python 3.12+)
```bash
cd minion2/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Frontend (React + Vite)
```bash
cd minion2/frontend
npm install
npm run dev
```
The dev server typically runs on **Port 5173**. Ensure the API endpoint in `App.jsx` points to `http://localhost:8001`.

---

## 🏛️ Database Sync (Persistence Protocol)

Minion 2.0 requires a Postgres schema named `minion`. The system automatically initializes tables on startup via SQLAlchemy.

### Initializing a Clean State
If you need to reset the mission history or cache:
- Execute `DELETE FROM minion.model_performance;` in your Postgres terminal.
- Or use the **Clear Cache** button in the dashboard.

## 📡 Port Registry
- **3015**: Unified Production (Frontend + API).
- **8001**: Standalone Backend API.
- **5173**: Frontend Development Mode.
- **11434**: Ollama LLM Bridge (Default).
