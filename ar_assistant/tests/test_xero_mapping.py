from app.integrations.xero import normalize_invoice

# Shape based on Xero's Invoice entity:
# https://developer.xero.com/documentation/api/accounting/invoices
SAMPLE_INVOICE = {
    "InvoiceID": "abc-123",
    "InvoiceNumber": "INV-2091",
    "Type": "ACCREC",
    "AmountDue": 950.0,
    "Total": 950.0,
    "DateString": "2026-06-20T00:00:00",
    "DueDateString": "2026-07-05T00:00:00",
    "Contact": {"Name": "Harbor Point Dental", "EmailAddress": "priya@harborpointdental.com"},
}


def test_normalizes_open_invoice():
    record = normalize_invoice(SAMPLE_INVOICE)
    assert record == {
        "customer_name": "Harbor Point Dental",
        "contact_name": None,
        "email": "priya@harborpointdental.com",
        "invoice_number": "INV-2091",
        "amount": 950.0,
        "issued_date": "2026-06-20",
        "due_date": "2026-07-05",
        "paid": False,
    }


def test_fully_paid_invoice_is_filtered_out():
    paid_invoice = {**SAMPLE_INVOICE, "AmountDue": 0}
    assert normalize_invoice(paid_invoice) is None


def test_falls_back_to_generated_invoice_number_when_missing():
    invoice = {**SAMPLE_INVOICE}
    del invoice["InvoiceNumber"]
    record = normalize_invoice(invoice)
    assert record["invoice_number"] == "XERO-abc-123"


def test_missing_contact_defaults_gracefully():
    invoice = {**SAMPLE_INVOICE, "Contact": {}}
    record = normalize_invoice(invoice)
    assert record["customer_name"] == "Unknown customer"
    assert record["email"] is None
