"""
Reconciliation Service
Orchestrates the full reconciliation workflow:
1. Parse both files
2. Classify entries using Grok AI
3. Run all 4 match types
4. Generate comprehensive report
"""

import uuid
from typing import Dict, Optional, List
from models.schemas import (
    ReconciliationReport, ReconciliationSummary, MatchResult, 
    MatchStatus, EntryType, LedgerEntry
)
from services.file_parser import parse_file
from services.matcher import match_entries
from services.grok_service import (
    classify_entries, extract_structured_data, analyze_document_structure
)
from database.db import SessionLocal
from services.database_service import save_reconciliation_to_db

def deduplicate_entries(entries: List[LedgerEntry]) -> List[LedgerEntry]:
    """
    Remove strictly duplicate entries from the list.
    Identifies duplicates based on Date, Voucher No, Debit, and Credit.
    """
    unique_entries = []
    seen = set()
    
    for entry in entries:
        # Create a unique key for the entry
        # We normalize voucher_no to avoid minor formatting differences
        from services.matcher import normalize_voucher_no
        vno = normalize_voucher_no(entry.voucher_no or "")
        
        # Key: (date, normalized_vno, debit, credit)
        key = (entry.date, vno, round(entry.debit, 2), round(entry.credit, 2))
        
        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)
            
    return unique_entries

# In-memory storage for reconciliation sessions
_sessions: Dict[str, ReconciliationReport] = {}

def create_session() -> str:
    """Create a new reconciliation session."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = ReconciliationReport(session_id=session_id)
    return session_id

def get_session(session_id: str) -> Optional[ReconciliationReport]:
    """Retrieve a session by ID."""
    return _sessions.get(session_id)

def update_session_step(session_id: str, step: str):
    """Add a processing step to the session's log."""
    session = get_session(session_id)
    if session:
        session.processing_steps.append(step)

async def run_reconciliation(
    session_id: str,
    vendor_files: List[dict],
    book_files: List[dict],
    use_ai: bool = True
) -> ReconciliationReport:
    """
    Run the full reconciliation process with multiple files per side.
    """
    report = _sessions.get(session_id)
    if not report:
        report = ReconciliationReport(session_id=session_id)
        _sessions[session_id] = report

    report.status = "processing"

    try:
        # ============================================
        # STEP 1: Parse Files (Multiple)
        # ============================================
        vendor_entries = []
        vendor_raw_parts = []
        
        for file_payload in vendor_files:
            update_session_step(session_id, f"Parsing vendor file: {file_payload['filename']}...")
            entries, raw = parse_file(file_payload['bytes'], file_payload['filename'], "vendor")
            
            # Adaptive logic: analyze structure if no entries found or anyway for better extraction
            if raw and use_ai:
                update_session_step(session_id, f"AI analyzing vendor ledger format: {file_payload['filename']}...")
                structure_context = analyze_document_structure(raw)
                
                if not entries or len(entries) < 2:
                    update_session_step(session_id, f"AI extracting from: {file_payload['filename']}...")
                    entries = extract_structured_data(raw, "vendor", structure_context)
            
            vendor_entries.extend(entries)
            vendor_raw_parts.append(raw)
        
        book_entries = []
        book_raw_parts = []
        
        for file_payload in book_files:
            update_session_step(session_id, f"Parsing book file: {file_payload['filename']}...")
            entries, raw = parse_file(file_payload['bytes'], file_payload['filename'], "book")
            
            if raw and use_ai:
                update_session_step(session_id, f"AI analyzing book ledger format: {file_payload['filename']}...")
                structure_context = analyze_document_structure(raw)
                
                if not entries or len(entries) < 2:
                    update_session_step(session_id, f"AI extracting from: {file_payload['filename']}...")
                    entries = extract_structured_data(raw, "book", structure_context)
            
            book_entries.extend(entries)
            book_raw_parts.append(raw)

        # ============================================
        # STEP 1B: Deduplicate Entries (Proactive logic)
        # ============================================
        v_original_count = len(vendor_entries)
        vendor_entries = deduplicate_entries(vendor_entries)
        if len(vendor_entries) < v_original_count:
            update_session_step(session_id, f"🧹 Removed {v_original_count - len(vendor_entries)} duplicate vendor entries.")

        b_original_count = len(book_entries)
        book_entries = deduplicate_entries(book_entries)
        if len(book_entries) < b_original_count:
            update_session_step(session_id, f"🧹 Removed {b_original_count - len(book_entries)} duplicate book entries.")

        # Re-assign IDs to combined dataset to ensure uniqueness
        for i, entry in enumerate(vendor_entries):
            entry.id = i + 1
        for i, entry in enumerate(book_entries):
            entry.id = i + 1

        if not vendor_entries:
            report.status = "error"
            report.error_message = "Could not extract entries from vendor ledger file. Please check the file format."
            return report

        if not book_entries:
            report.status = "error"
            report.error_message = "Could not extract entries from book ledger file. Please check the file format."
            return report

        # ============================================
        # STEP 2: Classify Entries
        # ============================================
        update_session_step(session_id, f"Classifying {len(vendor_entries)} vendor entries...")
        if use_ai:
            vendor_entries = classify_entries(vendor_entries)
        else:
            from services.grok_service import rule_based_classify
            for e in vendor_entries:
                e.entry_type = rule_based_classify(e)

        update_session_step(session_id, f"Classifying {len(book_entries)} book entries...")
        if use_ai:
            book_entries = classify_entries(book_entries)
        else:
            from services.grok_service import rule_based_classify
            for e in book_entries:
                e.entry_type = rule_based_classify(e)

        # ============================================
        # STEP 3: Match by Category
        # ============================================
        all_matched = []
        all_unmatched_vendor = []
        all_unmatched_book = []
        all_discrepancies = []

        match_types = [
            (EntryType.BILL, "bills"),
            (EntryType.CREDIT_NOTE, "credit notes"),
            (EntryType.TDS, "TDS entries"),
            (EntryType.PAYMENT, "payments"),
        ]

        category_stats = {}

        for entry_type, label in match_types:
            update_session_step(session_id, f"Matching {label}...")

            matched, unmatched_v, unmatched_b = match_entries(
                vendor_entries, book_entries, entry_type, use_ai=use_ai
            )

            # Separate discrepancies from matches
            real_matches = [m for m in matched if m.status in (MatchStatus.MATCHED, MatchStatus.NEEDS_REVIEW)]
            discrepancies = [m for m in matched if m.status == MatchStatus.DISCREPANCY]

            all_matched.extend(real_matches)
            all_unmatched_vendor.extend(unmatched_v)
            all_unmatched_book.extend(unmatched_b)
            all_discrepancies.extend(discrepancies)

            v_count = len([e for e in vendor_entries if e.entry_type == entry_type])
            b_count = len([e for e in book_entries if e.entry_type == entry_type])
            total = max(v_count, b_count)

            category_stats[entry_type] = {
                'matched': len(real_matches),
                'total': total
            }

        # Also handle UNKNOWN type entries
        update_session_step(session_id, "Matching remaining entries...")
        matched_unk, unmatched_v_unk, unmatched_b_unk = match_entries(
            vendor_entries, book_entries, EntryType.UNKNOWN, use_ai=use_ai
        )
        real_matches_unk = [m for m in matched_unk if m.status in (MatchStatus.MATCHED, MatchStatus.NEEDS_REVIEW)]
        disc_unk = [m for m in matched_unk if m.status == MatchStatus.DISCREPANCY]
        all_matched.extend(real_matches_unk)
        all_unmatched_vendor.extend(unmatched_v_unk)
        all_unmatched_book.extend(unmatched_b_unk)
        all_discrepancies.extend(disc_unk)

        # ============================================
        # STEP 4: Generate Summary
        # ============================================
        update_session_step(session_id, "Generating report...")

        total_entries = max(len(vendor_entries), len(book_entries))
        total_matched = len(all_matched)
        accuracy = (total_matched / total_entries * 100) if total_entries > 0 else 0

        summary = ReconciliationSummary(
            total_vendor_entries=len(vendor_entries),
            total_book_entries=len(book_entries),
            total_matched=total_matched,
            total_unmatched_vendor=len(all_unmatched_vendor),
            total_unmatched_book=len(all_unmatched_book),
            total_discrepancies=len(all_discrepancies),
            accuracy_rate=round(accuracy, 2),

            bills_matched=category_stats.get(EntryType.BILL, {}).get('matched', 0),
            bills_total=category_stats.get(EntryType.BILL, {}).get('total', 0),
            cn_matched=category_stats.get(EntryType.CREDIT_NOTE, {}).get('matched', 0),
            cn_total=category_stats.get(EntryType.CREDIT_NOTE, {}).get('total', 0),
            tds_matched=category_stats.get(EntryType.TDS, {}).get('matched', 0),
            tds_total=category_stats.get(EntryType.TDS, {}).get('total', 0),
            payments_matched=category_stats.get(EntryType.PAYMENT, {}).get('matched', 0),
            payments_total=category_stats.get(EntryType.PAYMENT, {}).get('total', 0),

            vendor_total_debit=sum(e.debit for e in vendor_entries),
            vendor_total_credit=sum(e.credit for e in vendor_entries),
            book_total_debit=sum(e.debit for e in book_entries),
            book_total_credit=sum(e.credit for e in book_entries),
            net_difference=abs(
                sum(e.debit - e.credit for e in vendor_entries) -
                sum(e.debit - e.credit for e in book_entries)
            )
        )

        report.summary = summary
        report.matched_entries = all_matched
        report.unmatched_vendor = all_unmatched_vendor
        report.unmatched_book = all_unmatched_book
        report.discrepancies = all_discrepancies
        report.status = "completed"

        update_session_step(session_id, f"✅ Reconciliation complete! {total_matched}/{total_entries} entries matched ({accuracy:.1f}% accuracy)")

    except Exception as e:
        report.status = "error"
        report.error_message = str(e)
        update_session_step(session_id, f"❌ Error: {str(e)}")

    # ============================================
    # STEP 5: Persist to Database
    # ============================================
    try:
        db = SessionLocal()
        save_reconciliation_to_db(db, report)
        db.close()
    except Exception as db_err:
        print(f"Database persistence error: {db_err}")

    _sessions[session_id] = report
    return report
