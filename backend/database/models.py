from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .db import Base
import datetime
import enum

class MatchStatus(enum.Enum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    DISCREPANCY = "discrepancy"
    NEEDS_REVIEW = "needs_review"

class EntryType(enum.Enum):
    BILL = "bill"
    CREDIT_NOTE = "credit_note"
    TDS = "tds"
    PAYMENT = "payment"
    UNKNOWN = "unknown"

class ReconcileSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True) # UUID or custom ID
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending") # pending, processing, completed, error
    vendor_party = Column(String, nullable=True)
    summary_json = Column(Text, nullable=True) # JSON blob for ReconciliationSummary
    error_message = Column(Text, nullable=True)

    entries = relationship("DbLedgerEntry", back_populates="session", cascade="all, delete-orphan")
    matches = relationship("DbMatchResult", back_populates="session", cascade="all, delete-orphan")

class DbLedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    source = Column(String) # "vendor" or "book"
    date = Column(String)
    particulars = Column(Text)
    voucher_type = Column(String)
    voucher_no = Column(String)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    balance = Column(Float, nullable=True)
    entry_type = Column(String, default="unknown")

    session = relationship("ReconcileSession", back_populates="entries")

class DbMatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    vendor_entry_id = Column(Integer, ForeignKey("ledger_entries.id"), nullable=True)
    book_entry_id = Column(Integer, ForeignKey("ledger_entries.id"), nullable=True)
    status = Column(String)
    match_type = Column(String)
    confidence = Column(Float, default=0.0)
    ai_reasoning = Column(Text)
    amount_difference = Column(Float, default=0.0)
    date_difference = Column(Integer, nullable=True)

    session = relationship("ReconcileSession", back_populates="matches")
    # Relationships to specific entries can be added here if needed for queries
