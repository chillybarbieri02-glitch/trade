"""Parses an invoice CSV and upserts customers/invoices into SQLite.

Expected columns: customer_name, contact_name, email, invoice_number, amount,
issued_date, due_date. Dates are ISO (YYYY-MM-DD).

This is the manual fallback for getting invoices in - the QuickBooks/Xero
sync (app/integrations/) is the preferred path since it needs no upkeep, but
CSV import still works for one-off imports or providers we don't integrate
with.
"""
import csv
import io

from .sync import REQUIRED_FIELDS, upsert_records


def import_csv(content: bytes) -> dict:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    missing = REQUIRED_FIELDS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    records = [{k: (v.strip() if v else v) for k, v in row.items()} for row in reader]
    result = upsert_records(records, update_existing=False)
    return {"imported": result["created"], "skipped": result["skipped"]}
