"""
Ledger Reconciliation Backend
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from routes.api import router as api_router
from database.db import engine, Base
import database.models as models

# Load environment variables (API keys, etc)
load_dotenv()

# Initialize Database
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ledger Reconciliation AI",
    description="AI-powered vendor vs book ledger reconciliation using Grok API",
    version="1.0.0"
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(api_router)

# Mount static files (React Frontend)
# This will serve files from backend/static if it exists
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Catch-all route to serve the React app."""
    # If not an API route and file doesn't exist, serve index.html
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Backend is running. Frontend build not found in /static."}


@app.get("/")
async def root():
    return {
        "app": "Ledger Reconciliation AI",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
