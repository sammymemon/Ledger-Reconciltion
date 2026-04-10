"""
API Routes
All REST endpoints for the ledger reconciliation app.
"""

import os
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from models.schemas import UploadResponse, ReconciliationReport, SettingsRequest
from services.reconciliation import (
    create_session, get_session, run_reconciliation, update_session_step
)
from services.grok_service import set_settings, get_api_key, test_connection
from database.db import get_db
from services.database_service import get_session_history, load_reconciliation_from_db


router = APIRouter(prefix="/api")

# In-memory file storage per session
_session_files = {}


from typing import List

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    vendor_files: List[UploadFile] = File(...),
    book_files: List[UploadFile] = File(...)
):
    """Upload multiple vendor and book ledger files."""
    # Validate file types
    allowed_extensions = {'.pdf', '.xlsx', '.xls'}
    
    vendor_data = []
    book_data = []

    for f in vendor_files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Vendor file {f.filename} must be PDF or Excel.")
        content = await f.read()
        vendor_data.append({'bytes': content, 'filename': f.filename})

    for f in book_files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Book file {f.filename} must be PDF or Excel.")
        content = await f.read()
        book_data.append({'bytes': content, 'filename': f.filename})

    # Create session
    session_id = create_session()

    # Store lists of files in memory
    _session_files[session_id] = {
        'vendor_files': vendor_data,
        'book_files': book_data,
    }

    return UploadResponse(
        session_id=session_id,
        vendor_entries=0, # Will be calculated during processing
        book_entries=0,
        message=f"{len(vendor_files)} vendor files and {len(book_files)} book files uploaded."
    )


@router.post("/reconcile/{session_id}")
async def start_reconciliation(session_id: str, background_tasks: BackgroundTasks):
    """Start the reconciliation process for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "processing":
        return {"status": "processing", "message": "Reconciliation already in progress"}

    files = _session_files.get(session_id)
    if not files:
        raise HTTPException(status_code=400, detail="No files found for this session. Please upload files first.")

    # Check API key
    api_key = get_api_key()
    use_ai = bool(api_key)

    if not use_ai:
        update_session_step(session_id, "⚠️ No Grok API key set. Using rule-based matching only.")

    # Run reconciliation in background
    background_tasks.add_task(
        run_reconciliation_task,
        session_id,
        files['vendor_files'],
        files['book_files'],
        use_ai
    )

    return {"status": "processing", "session_id": session_id, "message": "Reconciliation started"}


async def run_reconciliation_task(
    session_id: str,
    vendor_files: List[dict],
    book_files: List[dict],
    use_ai: bool
):
    """Background task to run reconciliation with multiple files."""
    await run_reconciliation(
        session_id, vendor_files, book_files, use_ai
    )


@router.get("/results/{session_id}")
async def get_results(session_id: str, db: Session = Depends(get_db)):
    """Get reconciliation results for a session (from memory or DB)."""
    # Try memory first
    session = get_session(session_id)
    if not session:
        # Try DB
        session = load_reconciliation_from_db(db, session_id)
        
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    """Get just the status and processing steps (lightweight polling endpoint)."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": session.status,
        "steps": session.processing_steps,
        "error": session.error_message
    }


@router.get("/settings")
async def get_settings():
    """Get current Grok API settings (masked)."""
    api_key = get_api_key()
    model = os.environ.get("GROK_MODEL", "grok-2-latest")
    
    if not api_key:
        return {"api_key_set": False, "model": model}
    
    # Mask key: gsk-xxxx...xxxx
    if len(api_key) > 8:
        masked = f"{api_key[:4]}****{api_key[-4:]}"
    else:
        masked = "****"
        
    return {
        "api_key_set": True,
        "masked_key": masked,
        "model": model
    }


@router.post("/settings")
async def save_settings(settings: SettingsRequest):
    """Save Grok API key and model."""
    if settings.api_key:
        # Basic validation
        if len(settings.api_key) < 10:
             raise HTTPException(status_code=400, detail="Invalid API key")
        
    set_settings(key=settings.api_key, model=settings.model)

    return {"message": "Settings saved successfully"}


@router.get("/settings/test")
async def test_api_connection():
    """Test if the Grok API key works."""
    api_key = get_api_key()
    if not api_key:
        return {"connected": False, "message": "No API key configured"}

    connected = test_connection()
    return {
        "connected": connected,
        "message": "Connection successful!" if connected else "Connection failed. Please check your API key."
    }


@router.get("/history")
async def get_history(db: Session = Depends(get_db)):
    """Get list of past reconciliation sessions from DB."""
    history = get_session_history(db)
    return [
        {
            "session_id": s.id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "status": s.status,
            "vendor_party": s.vendor_party,
            "summary": s.summary_json
        } for s in history
    ]

@router.delete("/history")
async def clear_history(db: Session = Depends(get_db)):
    """Clear all past history."""
    from database.models import ReconcileSession
    db.query(ReconcileSession).delete()
    db.commit()
    return {"status": "success", "message": "History cleared"}

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "api_key_set": bool(get_api_key()),
        "version": "1.0.0"
    }
