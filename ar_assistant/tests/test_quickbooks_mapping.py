from app.integrations.quickbooks import normalize_invoice

# Shape based on QuickBooks Online's Invoice entity:
# https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/invoice
SAMPLE_INVOICE = {
    "Id": "101",
    "DocNumber": "1041",
    "Balance": 4200.0,
    "TotalAmt": 4200.0,
    "TxnDate": "2026-05-01",
    "DueDate": "2026-05-31",
    "CustomerRef": {"value": "55", "name": "Blue Ridge Landscaping"},
}

CUSTOMER_LOOKUP = {"55": {"name": "Blue Ridge Landscaping", "email": "tom@blueridgelandscaping.com"}}


def test_normalizes_open_invoice():
    record = normalize_invoice(SAMPLE_INVOICE, CUSTOMER_LOOKUP)
    assert record == {
        "customer_name": "Blue Ridge Landscaping",
        "contact_name": None,
        "email": "tom@blueridgelandscaping.com",
        "invoice_number": "1041",
        "amount": 4200.0,
        "issued_date": "2026-05-01",
        "due_date": "2026-05-31",
        "paid": False,
    }


def test_fully_paid_invoice_is_filtered_out():
    paid_invoice = {**SAMPLE_INVOICE, "Balance": 0}
    assert normalize_invoice(paid_invoice, CUSTOMER_LOOKUP) is None


def test_falls_back_to_generated_invoice_number_when_doc_number_missing():
    invoice = {**SAMPLE_INVOICE}
    del invoice["DocNumber"]
    record = normalize_invoice(invoice, CUSTOMER_LOOKUP)
    assert record["invoice_number"] == "QBO-101"


def test_falls_back_to_customer_ref_name_when_lookup_misses():
    record = normalize_invoice(SAMPLE_INVOICE, customer_lookup={})
    assert record["customer_name"] == "Blue Ridge Landscaping"
    assert record["email"] is None
