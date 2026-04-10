# ====== STAGE 1: Build Frontend ======
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ====== STAGE 2: Run Backend ======
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for PostgreSQL and health checks
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (includes the data/ folder with .gitkeep)
COPY backend/ ./

# Copy built frontend from Stage 1 into backend/static
COPY --from=frontend-builder /app/frontend/dist ./static

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Use Gunicorn with Uvicorn worker
# We use a shell command to ensure $PORT is expanded correctly
CMD gunicorn main:app --bind 0.0.0.0:$PORT -w 2 -k uvicorn.workers.UvicornWorker --timeout 120 --access-logfile - --error-logfile -
