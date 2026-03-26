#!/bin/bash
# Minion 2.0 Unified Launcher
# (Python 3.14 Compatibility Layer)

# Colors
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🚀 Initializing Minion Hub 2.0 (High-Compatibility Mode)...${NC}"

# 1. Kill any ghost processes on Port 8001 (Backend) and 5173 (Frontend)
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

cd backend

# 2. Setup Virtual Env (Generic 3.14+ compatible)
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 3. Synchronize modernized dependencies
echo "Synchronizing Intelligence Logic (SQLAlchemy 2.0.35+)..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4. Start Backend (Using Explicit Module Path)
echo "Deploying Python Hub to http://localhost:8001..."
export PYTHONPATH=$(pwd)
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
BE_PID=$!

# 5. Launch Frontend
cd ../frontend
echo "Activating React Dashboard..."
npm install
npm run dev &
FE_PID=$!

# Wait and Cleanup
trap "kill $BE_PID $FE_PID; exit" SIGINT
wait
