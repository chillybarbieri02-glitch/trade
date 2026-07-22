"""Parses an invoice CSV and upserts customers/invoices into SQLite.

Expected columns: customer_name, contact_name, email, invoice_number, amount,
issued_date, due_date. Dates are ISO (YYYY-MM-DD).
"""
import csv
import io

from .database import get_conn


REQUIRED_COLUMNS = {"customer_name", "invoice_number", "amount", "issued_date", "due_date"}


def import_csv(content: bytes) -> dict:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    imported = 0
    skipped = 0
    with get_conn() as conn:
        for row in reader:
            customer_name = row["customer_name"].strip()
            if not customer_name:
                skipped += 1
                continue

            existing = conn.execute(
                "SELECT id FROM customers WHERE name = ?", (customer_name,)
            ).fetchone()
            if existing:
                customer_id = existing["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO customers (name, contact_name, email) VALUES (?, ?, ?)",
                    (customer_name, row.get("contact_name", "").strip() or None, row.get("email", "").strip() or None),
                )
                customer_id = cur.lastrowid

            invoice_number = row["invoice_number"].strip()
            already = conn.execute(
                "SELECT id FROM invoices WHERE customer_id = ? AND invoice_number = ?",
                (customer_id, invoice_number),
            ).fetchone()
            if already:
                skipped += 1
                continue

            conn.execute(
                """INSERT INTO invoices
                   (customer_id, invoice_number, amount, issued_date, due_date, status)
                   VALUES (?, ?, ?, ?, ?, 'open')""",
                (customer_id, invoice_number, float(row["amount"]), row["issued_date"].strip(), row["due_date"].strip()),
            )
            imported += 1

    return {"imported": imported, "skipped": skipped}
