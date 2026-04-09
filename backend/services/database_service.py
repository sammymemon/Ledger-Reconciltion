from sqlalchemy.orm import Session
from database.models import ReconcileSession, DbLedgerEntry, DbMatchResult
from models.schemas import ReconciliationReport, LedgerEntry, MatchResult, ReconciliationSummary
import json

def save_reconciliation_to_db(db: Session, report: ReconciliationReport):
    """Save full reconciliation results to the database."""
    # 1. Create or update session
    db_session = db.query(ReconcileSession).filter(ReconcileSession.id == report.session_id).first()
    if not db_session:
        db_session = ReconcileSession(id=report.session_id)
        db.add(db_session)
    
    db_session.status = report.status
    db_session.error_message = report.error_message
    if report.summary:
        db_session.summary_json = report.summary.json()
    
    # Party name detection (best guess from first entry particulars or source)
    if report.unmatched_vendor:
        db_session.vendor_party = "Complex Multi-File Analysis" # Placeholder or extract later
    
    # 2. Save Entries (Deduplicated or mapped)
    # Note: For performance, we only save entries once.
    # We clear old ones if this is a retry
    db.query(DbLedgerEntry).filter(DbLedgerEntry.session_id == report.session_id).delete()
    db.query(DbMatchResult).filter(DbMatchResult.session_id == report.session_id).delete()

    entry_map = {} # Map model Entry to DB Entry ID

    def add_entries(entries, source):
        for e in entries:
            db_e = DbLedgerEntry(
                session_id=report.session_id,
                source=source,
                date=e.date,
                particulars=e.particulars,
                voucher_type=e.voucher_type,
                voucher_no=e.voucher_no,
                debit=e.debit,
                credit=e.credit,
                balance=e.balance,
                entry_type=e.entry_type
            )
            db.add(db_e)
            db.flush() # Get ID
            entry_map[(source, e.id)] = db_e.id

    # Add all unique entries involved
    # Matches contain entries as well
    matched_v_entries = [m.vendor_entry for m in report.matched_entries if m.vendor_entry]
    matched_b_entries = [m.book_entry for m in report.matched_entries if m.book_entry]
    
    add_entries(matched_v_entries + report.unmatched_vendor, "vendor")
    add_entries(matched_b_entries + report.unmatched_book, "book")

    # 3. Save Match Results
    for m in report.matched_entries + report.discrepancies:
        db_m = DbMatchResult(
            session_id=report.session_id,
            vendor_entry_id=entry_map.get(("vendor", m.vendor_entry.id)) if m.vendor_entry else None,
            book_entry_id=entry_map.get(("book", m.book_entry.id)) if m.book_entry else None,
            status=m.status,
            match_type=m.match_type,
            confidence=m.confidence,
            ai_reasoning=m.ai_reasoning,
            amount_difference=m.amount_difference,
            date_difference=m.date_difference
        )
        db.add(db_m)

    db.commit()

def get_session_history(db: Session):
    """Get list of past sessions."""
    return db.query(ReconcileSession).order_by(ReconcileSession.created_at.desc()).all()

def load_reconciliation_from_db(db: Session, session_id: str) -> Optional[ReconciliationReport]:
    """Reconstruct a ReconciliationReport from the database."""
    db_session = db.query(ReconcileSession).filter(ReconcileSession.id == session_id).first()
    if not db_session:
        return None
    
    # Simplified reconstruction for now
    report = ReconciliationReport(
        session_id=db_session.id,
        status=db_session.status,
        error_message=db_session.error_message
    )
    if db_session.summary_json:
        report.summary = ReconciliationSummary.parse_raw(db_session.summary_json)
    
    # Deep reconstruction of entries/matches would go here
    # For now, we mainly need the summary and status for the UI history list
    return report
