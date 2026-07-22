from app.database import get_conn
from app.sync import upsert_records


def test_creates_new_customer_and_invoice(isolated_db):
    result = upsert_records(
        [{"customer_name": "Acme Co", "invoice_number": "INV-1", "amount": 500, "issued_date": "2026-01-01", "due_date": "2026-01-31"}]
    )
    assert result == {"created": 1, "updated": 0, "skipped": 0}


def test_default_skips_existing_invoice(isolated_db):
    record = {"customer_name": "Acme Co", "invoice_number": "INV-1", "amount": 500, "issued_date": "2026-01-01", "due_date": "2026-01-31"}
    upsert_records([record])
    result = upsert_records([record], update_existing=False)
    assert result == {"created": 0, "updated": 0, "skipped": 1}


def test_update_existing_refreshes_amount_and_status(isolated_db):
    record = {"customer_name": "Acme Co", "invoice_number": "INV-1", "amount": 500, "issued_date": "2026-01-01", "due_date": "2026-01-31"}
    upsert_records([record])

    updated_record = {**record, "amount": 100, "paid": True}
    result = upsert_records([updated_record], update_existing=True)
    assert result == {"created": 0, "updated": 1, "skipped": 0}

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE invoice_number = 'INV-1'").fetchone()
    assert row["amount"] == 100
    assert row["status"] == "paid"


def test_records_missing_required_fields_are_skipped(isolated_db):
    result = upsert_records([{"customer_name": "", "invoice_number": "INV-1", "amount": 1, "issued_date": "x", "due_date": "y"}])
    assert result == {"created": 0, "updated": 0, "skipped": 1}


def test_reuses_existing_customer_across_records(isolated_db):
    upsert_records(
        [
            {"customer_name": "Acme Co", "invoice_number": "INV-1", "amount": 100, "issued_date": "2026-01-01", "due_date": "2026-01-31"},
            {"customer_name": "Acme Co", "invoice_number": "INV-2", "amount": 200, "issued_date": "2026-02-01", "due_date": "2026-02-28"},
        ]
    )
    with get_conn() as conn:
        customers = conn.execute("SELECT * FROM customers").fetchall()
    assert len(customers) == 1
