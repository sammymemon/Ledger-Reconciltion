import pdfplumber
import os

files = [
    "S.K INTERIOR Needle Mached their side query.pdf",
    "statement_SkInterior (2).pdf"
]

for file in files:
    print(f"\n{'='*50}")
    print(f"FILE: {file}")
    print(f"{'='*50}")
    try:
        with pdfplumber.open(file) as pdf:
            # Extract first 3 pages
            for i, page in enumerate(pdf.pages[:3]):
                print(f"--- PAGE {i+1} ---")
                text = page.extract_text()
                print(text[:2000] if text else "[No text extracted]")
                
                # Check tables
                tables = page.extract_tables()
                if tables:
                    print(f"\nFOUND {len(tables)} TABLES")
                    for tidx, table in enumerate(tables):
                        print(f"Table {tidx+1} (first 3 rows):")
                        for row in table[:5]:
                            print(row)
    except Exception as e:
        print(f"Error reading {file}: {e}")
