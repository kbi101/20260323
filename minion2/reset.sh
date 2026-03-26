#!/bin/bash
# 🏛️ Minion Hub 2.0: Total Synaptic Reset
echo "🚀 Terminating all Hub processes (Uvicorn/Vite)..."
pkill -f uvicorn
pkill -f vite
sleep 2
echo "🏛️ Launching High-Fidelity Hub..."
./start.sh
