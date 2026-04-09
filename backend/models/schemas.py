from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import date


class EntryType(str, Enum):
    BILL = "bill"
    CREDIT_NOTE = "credit_note"
    TDS = "tds"
    PAYMENT = "payment"
    UNKNOWN = "unknown"


class MatchStatus(str, Enum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    DISCREPANCY = "discrepancy"
    NEEDS_REVIEW = "needs_review"


class LedgerEntry(BaseModel):
    """Represents a single entry in a ledger."""
    id: Optional[int] = None
    date: Optional[str] = None
    particulars: Optional[str] = None
    voucher_type: Optional[str] = None
    voucher_no: Optional[str] = None
    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None
    entry_type: EntryType = EntryType.UNKNOWN
    raw_text: Optional[str] = None
    source: Optional[str] = None  # "vendor" or "book"


class MatchResult(BaseModel):
    """Represents a match between two ledger entries."""
    vendor_entry: Optional[LedgerEntry] = None
    book_entry: Optional[LedgerEntry] = None
    status: MatchStatus = MatchStatus.UNMATCHED
    match_type: EntryType = EntryType.UNKNOWN
    confidence: float = 0.0
    ai_reasoning: Optional[str] = None
    amount_difference: float = 0.0
    date_difference: Optional[int] = None  # days


class ReconciliationSummary(BaseModel):
    """Summary statistics for the reconciliation."""
    total_vendor_entries: int = 0
    total_book_entries: int = 0
    total_matched: int = 0
    total_unmatched_vendor: int = 0
    total_unmatched_book: int = 0
    total_discrepancies: int = 0
    accuracy_rate: float = 0.0

    # By category
    bills_matched: int = 0
    bills_total: int = 0
    cn_matched: int = 0
    cn_total: int = 0
    tds_matched: int = 0
    tds_total: int = 0
    payments_matched: int = 0
    payments_total: int = 0

    # Amounts
    vendor_total_debit: float = 0.0
    vendor_total_credit: float = 0.0
    book_total_debit: float = 0.0
    book_total_credit: float = 0.0
    net_difference: float = 0.0


class ReconciliationReport(BaseModel):
    """Complete reconciliation report."""
    session_id: str
    status: str = "pending"  # pending, processing, completed, error
    summary: Optional[ReconciliationSummary] = None
    matched_entries: List[MatchResult] = []
    unmatched_vendor: List[LedgerEntry] = []
    unmatched_book: List[LedgerEntry] = []
    discrepancies: List[MatchResult] = []
    processing_steps: List[str] = []
    error_message: Optional[str] = None


class UploadResponse(BaseModel):
    """Response after file upload."""
    session_id: str
    vendor_entries: int = 0
    book_entries: int = 0
    message: str = ""


class SettingsRequest(BaseModel):
    """Request to save API settings."""
    api_key: Optional[str] = None
    model: Optional[str] = None
