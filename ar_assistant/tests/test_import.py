import pytest

from app import importer
from app.database import get_conn

SAMPLE_CSV = b"""customer_name,contact_name,email,invoice_number,amount,issued_date,due_date
Acme Co,Jane Doe,jane@acme.com,INV-1,500.00,2026-01-01,2026-01-31
Acme Co,Jane Doe,jane@acme.com,INV-2,750.50,2026-02-01,2026-03-01
"""


def test_import_creates_customer_and_invoices(isolated_db):
    result = importer.import_csv(SAMPLE_CSV)
    assert result == {"imported": 2, "skipped": 0}

    with get_conn() as conn:
        customers = conn.execute("SELECT * FROM customers").fetchall()
        invoices = conn.execute("SELECT * FROM invoices").fetchall()

    assert len(customers) == 1
    assert customers[0]["name"] == "Acme Co"
    assert len(invoices) == 2
    assert {inv["invoice_number"] for inv in invoices} == {"INV-1", "INV-2"}


def test_reimporting_same_csv_skips_duplicates(isolated_db):
    importer.import_csv(SAMPLE_CSV)
    result = importer.import_csv(SAMPLE_CSV)
    assert result == {"imported": 0, "skipped": 2}


def test_missing_required_column_raises(isolated_db):
    bad_csv = b"customer_name,amount\nAcme,100\n"
    with pytest.raises(ValueError):
        importer.import_csv(bad_csv)
