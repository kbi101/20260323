# 🏗️ Stage 1: Build the React Frontend (Minion 2.0 Node)
FROM node:20-alpine AS build-frontend
WORKDIR /frontend
# Using the parent context to find the frontend source
COPY minion2/frontend/package*.json ./
RUN npm install
COPY minion2/frontend/ .
RUN npm run build

# 🏎️ Stage 2: Unified Python Environment (Minion 2.0 Core)
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies (including Playwright support for OSINT)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates lsb-release gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir setuptools
COPY minion2/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (in-container fallback for OSINT when CDP isn't reachable)
RUN playwright install --with-deps chromium

# Copy built frontend static assets from Stage 1 into a top-level distribution hub
# This prevents volume mounts from /app (like for dev) from overwriting our static bundle
COPY --from=build-frontend /frontend/dist /dist

# Copy backend source
COPY minion2/backend/ ./

# Environment Defaults for Unified Service
ENV PORT=3015
ENV DATABASE_URL=sqlite+aiosqlite:///minion_memory.db
ENV LLM_URL=http://host.docker.internal:11434
ENV FRONTEND_DIR=/dist

EXPOSE 3015

# Deploy the Unified Hub: One Port, Two Souls
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3015"]
