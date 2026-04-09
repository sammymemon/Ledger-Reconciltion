"""
File Parser Service
Parses PDF and Excel files to extract ledger entries.
Uses pdfplumber for PDFs and openpyxl/pandas for Excel files.
"""

import pdfplumber
import pandas as pd
import re
import io
from typing import List, Tuple
from models.schemas import LedgerEntry


def clean_amount(value) -> float:
    """Clean and convert amount strings to float."""
    if value is None or value == "" or value == "-":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Remove commas, spaces, currency symbols
    cleaned = re.sub(r'[₹,$\s]', '', str(value))
    # Handle parentheses for negative numbers
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    # Handle Dr/Cr suffixes
    cleaned = cleaned.replace('Dr', '').replace('Cr', '').replace('dr', '').replace('cr', '').strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def clean_text(value) -> str:
    """Clean text values."""
    if value is None:
        return ""
    return str(value).strip()


def detect_columns(headers: List[str]) -> dict:
    """
    Auto-detect column mapping from header names.
    Returns a dict mapping our standard fields to column indices.
    """
    mapping = {
        'date': None,
        'particulars': None,
        'voucher_type': None,
        'voucher_no': None,
        'debit': None,
        'credit': None,
        'balance': None,
    }

    date_keywords = ['date', 'dt', 'dated', 'txn date', 'transaction date', 'दिनांक']
    particulars_keywords = ['particulars', 'narration', 'description', 'detail', 'party', 'name', 'विवरण']
    vtype_keywords = ['voucher type', 'vch type', 'type', 'vch. type', 'v.type', 'vtype']
    vno_keywords = ['voucher no', 'vch no', 'vch. no', 'ref no', 'ref', 'reference', 'bill no', 'invoice no', 'v.no', 'vno']
    debit_keywords = ['debit', 'dr', 'debit amount', 'debit amt', 'dr amount', 'dr.']
    credit_keywords = ['credit', 'cr', 'credit amount', 'credit amt', 'cr amount', 'cr.']
    balance_keywords = ['balance', 'closing balance', 'running balance', 'bal']

    for idx, header in enumerate(headers):
        h = str(header).lower().strip()

        if mapping['date'] is None and any(k in h for k in date_keywords):
            mapping['date'] = idx
        elif mapping['voucher_type'] is None and any(k == h or k in h for k in vtype_keywords):
            mapping['voucher_type'] = idx
        elif mapping['voucher_no'] is None and any(k == h or k in h for k in vno_keywords):
            mapping['voucher_no'] = idx
        elif mapping['particulars'] is None and any(k in h for k in particulars_keywords):
            mapping['particulars'] = idx
        elif mapping['debit'] is None and any(k == h or k in h for k in debit_keywords):
            mapping['debit'] = idx
        elif mapping['credit'] is None and any(k == h or k in h for k in credit_keywords):
            mapping['credit'] = idx
        elif mapping['balance'] is None and any(k in h for k in balance_keywords):
            mapping['balance'] = idx

    return mapping


def rows_to_entries(rows: List[List], col_mapping: dict, source: str) -> List[LedgerEntry]:
    """Convert raw rows to LedgerEntry objects using column mapping."""
    entries = []
    entry_id = 1

    for row in rows:
        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
            continue

        # Extract values using mapping
        date_val = clean_text(row[col_mapping['date']]) if col_mapping['date'] is not None and col_mapping['date'] < len(row) else None
        particulars = clean_text(row[col_mapping['particulars']]) if col_mapping['particulars'] is not None and col_mapping['particulars'] < len(row) else ""
        vtype = clean_text(row[col_mapping['voucher_type']]) if col_mapping['voucher_type'] is not None and col_mapping['voucher_type'] < len(row) else ""
        vno = clean_text(row[col_mapping['voucher_no']]) if col_mapping['voucher_no'] is not None and col_mapping['voucher_no'] < len(row) else ""
        debit = clean_amount(row[col_mapping['debit']]) if col_mapping['debit'] is not None and col_mapping['debit'] < len(row) else 0.0
        credit = clean_amount(row[col_mapping['credit']]) if col_mapping['credit'] is not None and col_mapping['credit'] < len(row) else 0.0
        balance = clean_amount(row[col_mapping['balance']]) if col_mapping['balance'] is not None and col_mapping['balance'] < len(row) else None

        # Skip rows that look like headers or totals
        if particulars.lower() in ['total', 'grand total', 'closing balance', 'opening balance', '']:
            if not date_val and debit == 0 and credit == 0:
                continue

        # Skip if no meaningful data
        if not date_val and not particulars and debit == 0 and credit == 0:
            continue

        raw = " | ".join([str(c) for c in row if c is not None])

        entry = LedgerEntry(
            id=entry_id,
            date=date_val if date_val else None,
            particulars=particulars,
            voucher_type=vtype,
            voucher_no=vno,
            debit=debit,
            credit=credit,
            balance=balance,
            raw_text=raw,
            source=source
        )
        entries.append(entry)
        entry_id += 1

    return entries


def parse_pdf(file_bytes: bytes, source: str = "vendor") -> Tuple[List[LedgerEntry], str]:
    """
    Parse a PDF file and extract ledger entries.
    Returns a tuple of (entries, raw_text_for_ai).
    """
    entries = []
    all_text = []
    all_rows = []
    headers = None

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # Extract text for AI fallback
            text = page.extract_text()
            if text:
                all_text.append(text)

            # Try to extract tables
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                for row_idx, row in enumerate(table):
                    if headers is None:
                        # First row with enough non-empty cells is likely the header
                        non_empty = sum(1 for cell in row if cell and str(cell).strip())
                        if non_empty >= 3:
                            headers = row
                            continue

                    all_rows.append(row)

    raw_text = "\n".join(all_text)

    if headers and all_rows:
        col_mapping = detect_columns(headers)
        entries = rows_to_entries(all_rows, col_mapping, source)

    return entries, raw_text


def parse_excel(file_bytes: bytes, source: str = "vendor") -> Tuple[List[LedgerEntry], str]:
    """
    Parse an Excel file and extract ledger entries.
    Returns a tuple of (entries, raw_text_for_ai).
    """
    df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')

    # Remove completely empty rows
    df = df.dropna(how='all')

    if df.empty:
        return [], ""

    # Detect columns
    headers = [str(col) for col in df.columns.tolist()]
    col_mapping = detect_columns(headers)

    # Convert DataFrame to list of lists
    rows = df.values.tolist()

    # If column detection failed, try finding header row in data
    if all(v is None for v in col_mapping.values()):
        for idx, row in enumerate(rows):
            test_headers = [str(c) if c is not None else '' for c in row]
            test_mapping = detect_columns(test_headers)
            if sum(1 for v in test_mapping.values() if v is not None) >= 3:
                col_mapping = test_mapping
                rows = rows[idx + 1:]
                headers = test_headers
                break

    entries = rows_to_entries(rows, col_mapping, source)

    # Build raw text for AI
    raw_text = df.to_string()

    return entries, raw_text


def parse_file(file_bytes: bytes, filename: str, source: str = "vendor") -> Tuple[List[LedgerEntry], str]:
    """
    Parse a file based on its extension.
    Returns (entries, raw_text).
    """
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''

    if ext == 'pdf':
        return parse_pdf(file_bytes, source)
    elif ext in ('xlsx', 'xls'):
        return parse_excel(file_bytes, source)
    else:
        raise ValueError(f"Unsupported file format: .{ext}. Please upload PDF or Excel files.")
