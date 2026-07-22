"""Shared upsert logic for getting invoice records into SQLite.

Used by both the manual CSV importer and the QuickBooks/Xero sync jobs, so
there is exactly one place that decides how a customer or invoice.upstream
record turns into rows in `customers`/`invoices`.

A "record" is a plain dict with keys: customer_name, contact_name, email,
invoice_number, amount, issued_date, due_date, and optionally `paid` (bool -
only accounting-software syncs set this; CSV rows are always treated as
open, matching prior behavior).
"""
from .database import get_conn

REQUIRED_FIELDS = {"customer_name", "invoice_number", "amount", "issued_date", "due_date"}


def _get_or_create_customer(conn, customer_name, contact_name, email):
    existing = conn.execute("SELECT id FROM customers WHERE name = ?", (customer_name,)).fetchone()
    if existing:
        return existing["id"]
    cur = conn.execute(
        "INSERT INTO customers (name, contact_name, email) VALUES (?, ?, ?)",
        (customer_name, contact_name or None, email or None),
    )
    return cur.lastrowid


def upsert_records(records: list[dict], *, update_existing: bool = False) -> dict:
    """Insert new invoices. If update_existing is True, also refreshes
    amount/due_date/status on invoices that already exist (accounting-software
    sync case, where a balance can change between syncs). If False, an
    existing invoice_number for the same customer is left untouched and
    counted as skipped (manual CSV import case).
    """
    created = 0
    updated = 0
    skipped = 0

    with get_conn() as conn:
        for record in records:
            customer_name = (record.get("customer_name") or "").strip()
            invoice_number = (record.get("invoice_number") or "").strip()
            if not customer_name or not invoice_number:
                skipped += 1
                continue

            customer_id = _get_or_create_customer(
                conn, customer_name, (record.get("contact_name") or "").strip(), (record.get("email") or "").strip()
            )

            existing = conn.execute(
                "SELECT id, status FROM invoices WHERE customer_id = ? AND invoice_number = ?",
                (customer_id, invoice_number),
            ).fetchone()

            status = "paid" if record.get("paid") else "open"

            if existing:
                if not update_existing:
                    skipped += 1
                    continue
                conn.execute(
                    "UPDATE invoices SET amount = ?, due_date = ?, issued_date = ?, status = ? WHERE id = ?",
                    (
                        float(record["amount"]),
                        record["due_date"],
                        record["issued_date"],
                        status,
                        existing["id"],
                    ),
                )
                updated += 1
                continue

            conn.execute(
                """INSERT INTO invoices
                   (customer_id, invoice_number, amount, issued_date, due_date, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (customer_id, invoice_number, float(record["amount"]), record["issued_date"], record["due_date"], status),
            )
            created += 1

    return {"created": created, "updated": updated, "skipped": skipped}
