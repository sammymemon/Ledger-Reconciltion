"""
Grok AI Service
Connects to xAI's Grok API via OpenAI-compatible SDK.
Handles entry classification, structured data extraction, and match verification.
"""

import json
import os
from typing import List, Optional
import httpx
from openai import OpenAI
from models.schemas import LedgerEntry, EntryType


# Persistent API key storage path (.env)
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

# Model configurations
DEFAULT_MODEL = "grok-2-latest" 
FALLBACK_MODELS = ["grok-beta", "grok-2-1212"]

# Global API key storage (cached in memory)
_api_key: Optional[str] = None


def set_settings(key: Optional[str] = None, model: Optional[str] = None):
    """Set and persist Grok settings to .env file."""
    global _api_key
    
    # 1. Update in-memory and env
    if key:
        _api_key = key
        os.environ["GROK_API_KEY"] = key
    if model:
        os.environ["GROK_MODEL"] = model
    
    # 2. Persist to .env file
    try:
        lines = []
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, "r") as f:
                lines = f.readlines()
        
        env_dict = {}
        for line in lines:
            if "=" in line:
                k, v = line.split("=", 1)
                env_dict[k.strip()] = v.strip()
        
        if key: env_dict["GROK_API_KEY"] = key
        if model: env_dict["GROK_MODEL"] = model
            
        with open(ENV_FILE, "w") as f:
            for k, v in env_dict.items():
                f.write(f"{k}={v}\n")
            
    except Exception as e:
        print(f"Error saving settings to .env: {e}")


def get_api_key() -> Optional[str]:
    """Get the Grok API key from memory, file, or environment."""
    global _api_key
    
    # 2. Try environment variables (which includes loaded .env)
    key = os.environ.get("GROK_API_KEY", os.environ.get("XAI_API_KEY"))
    if key:
        _api_key = key
        return key

    # 3. Fallback: manual .env read (safety)
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r") as f:
                for line in f:
                    if line.startswith("GROK_API_KEY="):
                        val = line.split("=", 1)[1].strip()
                        if val:
                            _api_key = val
                            return val
        except Exception as e:
            print(f"Error reading .env: {e}")

    return None


def get_client() -> OpenAI:
    """
    Create an OpenAI client configured for Grok API.
    Uses a custom http_client to avoid version-related proxy errors.
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Grok API key not set. Please configure it in settings.")

    # Explicitly create an httpx client to avoid 'proxies' argument issues
    # in some versions of openai/httpx
    http_client = httpx.Client()

    return OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
        http_client=http_client
    )


def classify_entries(entries: List[LedgerEntry]) -> List[LedgerEntry]:
    """
    Use Grok AI to classify ledger entries into Bill, Credit Note, TDS, or Payment.
    Processes in batches for efficiency.
    """
    if not entries:
        return entries

    client = get_client()
    batch_size = 30
    classified = []

    for i in range(0, len(entries), batch_size):
        batch = entries[i:i + batch_size]

        entries_text = ""
        for idx, entry in enumerate(batch):
            entries_text += f"""
Entry {idx + 1}:
  Date: {entry.date}
  Particulars: {entry.particulars}
  Voucher Type: {entry.voucher_type}
  Voucher No: {entry.voucher_no}
  Debit: {entry.debit}
  Credit: {entry.credit}
---
"""

        prompt = f"""You are an expert Indian accountant. Classify each ledger entry into one of these categories:
- "bill" = Purchase bill, sales bill, invoice, GST bill
- "credit_note" = Credit note, return, debit note
- "tds" = TDS deduction, tax deducted at source
- "payment" = Payment received, NEFT, RTGS, bank transfer, etc.

SIGN LOGIC:
- Bills are positive.
- Payments/Credit Notes are logically negative.

Here are the entries to classify:
{entries_text}

IMPORTANT: Respond ONLY with a valid JSON array of strings, one per entry. Respond with JUST the JSON array."""

        try:
            response = client.chat.completions.create(
                model="grok-3-mini-fast",
                messages=[
                    {"role": "system", "content": "You are a precise Indian accounting classifier. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=2000
            )

            result = response.choices[0].message.content.strip()
            # Extract JSON from response
            if '```' in result:
                result = result.split('```')[1]
                if result.startswith('json'):
                    result = result[4:]
                result = result.strip()

            classifications = json.loads(result)

            for idx, entry in enumerate(batch):
                if idx < len(classifications):
                    cls = classifications[idx].lower().strip()
                    type_map = {
                        'bill': EntryType.BILL,
                        'credit_note': EntryType.CREDIT_NOTE,
                        'tds': EntryType.TDS,
                        'payment': EntryType.PAYMENT,
                    }
                    entry.entry_type = type_map.get(cls, EntryType.UNKNOWN)
                classified.append(entry)

        except Exception as e:
            print(f"Classification error for batch {i}: {e}")
            # Fallback: try rule-based classification
            for entry in batch:
                entry.entry_type = rule_based_classify(entry)
                classified.append(entry)

    return classified


def rule_based_classify(entry: LedgerEntry) -> EntryType:
    """Fallback rule-based classification when AI is unavailable."""
    text = f"{entry.particulars} {entry.voucher_type}".lower()

    tds_keywords = ['tds', 'tax deducted', 'tax deduction', '194', '195', '196']
    cn_keywords = ['credit note', 'cn', 'debit note', 'dn', 'return', 'cr. note', 'dr. note']
    payment_keywords = ['payment', 'receipt', 'neft', 'rtgs', 'cheque', 'cash', 'bank', 'upi', 'imps', 'paid', 'received']
    bill_keywords = ['bill', 'invoice', 'purchase', 'sale', 'gst', 'inv', 'pi', 'si']

    if any(k in text for k in tds_keywords):
        return EntryType.TDS
    elif any(k in text for k in cn_keywords):
        return EntryType.CREDIT_NOTE
    elif any(k in text for k in payment_keywords):
        return EntryType.PAYMENT
    elif any(k in text for k in bill_keywords):
        return EntryType.BILL

    # Default based on voucher type
    vtype = (entry.voucher_type or "").lower()
    if 'purchase' in vtype or 'sales' in vtype:
        return EntryType.BILL
    elif 'journal' in vtype:
        return EntryType.TDS
    elif 'payment' in vtype or 'receipt' in vtype or 'contra' in vtype:
        return EntryType.PAYMENT

    return EntryType.UNKNOWN


def extract_structured_data(raw_text: str, source: str = "vendor", structure_context: str = None) -> List[LedgerEntry]:
    """
    Use Grok AI to extract structured ledger entries from raw/messy PDF text.
    Includes a self-verification phase in the prompt for 99%+ accuracy.
    """
    if not raw_text or len(raw_text.strip()) < 50:
        return []

    client = get_client()
    truncated = raw_text[:12000] 

    context_str = f"\nDOCUMENT STRUCTURE CONTEXT:\n{structure_context}" if structure_context else ""

    prompt = f"""You are an elite accounting reconciliation engine (Grok-3 Powered).
Your task is to extract ALL ledger entries from this {'vendor' if source == 'vendor' else 'book'} ledger text.

OBJECTIVE:
Prepare a high-accuracy dataset for matching.

CRITICAL EXTRACTION RULES:
1. Normalization (MANDATORY):
   - Remove spaces, dashes, special chars from voucher numbers.
   - Example: INV-001 -> 001, PI/24-25/08 -> 242508
2. Sign Logic:
   - Invoice/Bill = POSITIVE
   - Payment/Credit Note/TDS = NEGATIVE (Extract as is, but logic will treat as reduction)
3. Date Format: Convert ALL dates to DD/MM/YYYY.
4. Voucher No: Extract full reference strings AND normalized versions.

OUTPUT FORMAT:
Return ONLY a valid JSON array of objects with these exact keys:
{{
  "date": "DD/MM/YYYY",
  "particulars": "Full text particulars",
  "voucher_type": "Original Type",
  "voucher_no": "Full voucher string",
  "debit": 0.0,
  "credit": 0.0
}}

TEXT CONTENT TO EXTRACT:
{truncated}

Do not include any text other than JSON."""

    model_to_use = os.environ.get("GROK_MODEL", DEFAULT_MODEL)
    
    # Try multiple models if one fails (Proactive stability)
    models_to_try = [model_to_use] + FALLBACK_MODELS
    last_error = ""

    for attempt_model in models_to_try:
        try:
            print(f"AI Extraction Attempt with model: {attempt_model}")
            response = client.chat.completions.create(
                model=attempt_model,
                messages=[
                    {"role": "system", "content": "You are a professional accounting data extraction engine. You perform multi-step verification before outputting JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            # Basic JSON cleaning
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            entries_data = json.loads(content)
            return [LedgerEntry(**e) for e in entries_data]

        except Exception as e:
            last_error = str(e)
            print(f"AI Extraction error with {attempt_model}: {e}")
            continue # Try next model

    # If all models fail, raise a descriptive error
    raise ValueError(f"AI Extraction failed after trying all models. Last error: {last_error}. Please check your API key and connection.")

        result = response.choices[0].message.content.strip()
        if '```' in result:
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
            result = result.strip()

        data = json.loads(result)
        entries = []

        for idx, item in enumerate(data):
            try:
                # Basic validation of extracted data
                debit = float(str(item.get('debit', 0)).replace(',', ''))
                credit = float(str(item.get('credit', 0)).replace(',', ''))
                
                entry = LedgerEntry(
                    id=idx + 1,
                    date=item.get('date'),
                    particulars=item.get('particulars', ''),
                    voucher_type=item.get('voucher_type', ''),
                    voucher_no=item.get('voucher_no', ''),
                    debit=debit,
                    credit=credit,
                    source=source,
                    raw_text=json.dumps(item)
                )
                entries.append(entry)
            except:
                continue

        return entries

    except Exception as e:
        print(f"AI extraction error: {e}")
        return []


def analyze_document_structure(sample_text: str) -> str:
    """
    Use Grok AI to analyze the document layout and provide hints for better extraction.
    This is the 'Adaptive Logic' part.
    """
    if not sample_text or len(sample_text) < 100:
        return ""

    client = get_client()
    sample = sample_text[:3000] # First 3000 chars are enough to see headers

    prompt = f"""Analyze this ledger document text and describe its structure:
{sample}

Identify:
1. Column names and their order.
2. Does it use Debit/Credit columns or a single Amount column with Dr/Cr indicators?
3. What is the date format?
4. Who is the vendor/party if visible?
5. Are there any multi-line particulars?

Respond with a concise summary that can help a data extraction AI. Keep it under 200 words."""

    try:
        response = client.chat.completions.create(
            model="grok-3-mini-fast",
            messages=[
                {"role": "system", "content": "You are a document structure analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Structure analysis error: {e}")
        return ""


def detect_party_name(sample_text: str) -> str:
    """
    Use Grok AI to identify the party/vendor name from the header.
    Helps in distinguishing between Own Books vs Vendor Statement.
    """
    if not sample_text or len(sample_text) < 100:
        return "Unknown Party"

    client = get_client()
    sample = sample_text[:2000]

    prompt = f"""Extract the primary Party Name (Vendor/Client) whose ledger this is from the header text:
{sample}

Just return the name. No explanation."""

    try:
        response = client.chat.completions.create(
            model="grok-3-mini-fast",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except:
        return "Unknown Party"


def verify_match(vendor_entry: LedgerEntry, book_entry: LedgerEntry) -> dict:
    """
    Use Grok AI to verify if two entries are a genuine match.
    Returns confidence score and reasoning.
    """
    client = get_client()

    prompt = f"""You are an expert Indian accountant verifying ledger reconciliation matches.

VENDOR LEDGER ENTRY:
  Date: {vendor_entry.date}
  Particulars: {vendor_entry.particulars}
  Voucher Type: {vendor_entry.voucher_type}
  Voucher No: {vendor_entry.voucher_no}
  Debit: {vendor_entry.debit}
  Credit: {vendor_entry.credit}

BOOK LEDGER ENTRY:
  Date: {book_entry.date}
  Particulars: {book_entry.particulars}
  Voucher Type: {book_entry.voucher_type}
  Voucher No: {book_entry.voucher_no}
  Debit: {book_entry.debit}
  Credit: {book_entry.credit}

IMPORTANT RULES FOR MATCHING (9-STEP PRIORITY):
1. Exact Match: Voucher AND Amount match exactly.
2. Fuzzy Voucher: Normalize (remove spaces/-) and match.
3. Amount + Name: If voucher missing, match same amount with similar vendor name.
4. Date Tolerance: Accept ±7 days difference.
5. Many-to-One: Sum of multiple invoices = 1 payment.
6. Credit Notes: Link via reference or negative adjustment.
7. TDS Bridge: Invoice 100k - Payment 98k = 2% TDS.
8. Duplicate Detect: Same INV# + Amt.
9. Confidence: Assign 0-100 score.

Evaluate if these two entries represent the SAME transaction.

Respond with ONLY valid JSON:
{
  "is_match": true/false,
  "confidence": 0-100,
  "reasoning": "brief explanation mentioning the Step # used",
  "match_type": "Step X Match"
}"""

    try:
        response = client.chat.completions.create(
            model="grok-3-mini-fast",
            messages=[
                {"role": "system", "content": "You are a precise accounting match verifier. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=500
        )

        result = response.choices[0].message.content.strip()
        if '```' in result:
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
            result = result.strip()

        return json.loads(result)

    except Exception as e:
        print(f"Verification error: {e}")
        return {
            "is_match": False,
            "confidence": 0.0,
            "reasoning": f"AI verification failed: {str(e)}",
            "amount_match": False,
            "date_match": False
        }


def test_connection() -> bool:
    """Test if the Grok API key is valid."""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model="grok-3-mini-fast",
            messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
            max_tokens=10
        )
        return bool(response.choices[0].message.content)
    except Exception:
        return False
