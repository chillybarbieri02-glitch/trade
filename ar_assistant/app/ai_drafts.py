"""Drafts a collection-reminder email for one invoice.

Uses the Anthropic API when ANTHROPIC_API_KEY and ANTHROPIC_MODEL are both
set, so the tone and phrasing adapt to the customer's history and the stage
of the collection (friendly -> firm -> final -> escalate). Falls back to a
deterministic template otherwise, so the app runs end-to-end with no API key.
"""
import os

STAGE_TONE = {
    "friendly": "warm and low-pressure, assuming this is simply an oversight",
    "firm": "polite but direct, clearly restating the amount and due date, asking for a payment date",
    "final": "serious and unambiguous, stating this is a final notice before escalation, while remaining professional",
    "escalate": "formal, noting the account is being referred for collections/legal follow-up unless paid immediately",
}

FALLBACK_OPENERS = {
    "friendly": "This is a friendly reminder that invoice {invoice_number} for ${amount:,.2f} was due on {due_date}.",
    "firm": "Invoice {invoice_number} for ${amount:,.2f} is now {days_overdue} days past its {due_date} due date.",
    "final": "This is a final notice: invoice {invoice_number} for ${amount:,.2f} remains unpaid {days_overdue} days after its due date of {due_date}.",
    "escalate": "Invoice {invoice_number} for ${amount:,.2f}, due {due_date}, is {days_overdue} days overdue and is now being escalated.",
}


def _fallback_draft(customer_name, contact_name, invoice_number, amount, due_date, days_overdue, stage):
    greeting = f"Hi {contact_name}," if contact_name else f"Hello {customer_name} team,"
    opener = FALLBACK_OPENERS[stage].format(
        invoice_number=invoice_number, amount=amount, due_date=due_date, days_overdue=days_overdue
    )
    closing = {
        "friendly": "Could you let us know when we can expect payment? Happy to resend the invoice if it's easier to find.",
        "firm": "Please send payment or a specific payment date by return email so we can update our records.",
        "final": "Please remit payment in full within 5 business days to avoid further action.",
        "escalate": "If payment is not received within 48 hours, this account will be referred to our collections partner.",
    }[stage]
    return f"{greeting}\n\n{opener} {closing}\n\nThank you,\nAccounts Receivable"


def generate_draft(*, customer_name, contact_name, invoice_number, amount, due_date, days_overdue, stage):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL")

    if not api_key or not model:
        return _fallback_draft(customer_name, contact_name, invoice_number, amount, due_date, days_overdue, stage)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            f"Draft a short collection-reminder email for an unpaid invoice.\n"
            f"Customer: {customer_name}"
            + (f" (contact: {contact_name})" if contact_name else "")
            + f"\nInvoice number: {invoice_number}\n"
            f"Amount due: ${amount:,.2f}\n"
            f"Original due date: {due_date}\n"
            f"Days overdue: {days_overdue}\n"
            f"Desired tone for this stage ('{stage}'): {STAGE_TONE[stage]}.\n"
            "Keep it under 120 words, no subject line, sign off as 'Accounts Receivable'."
        )
        response = client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text")).strip()
    except Exception:
        # API unreachable, bad key, rate-limited, etc. - never block collections on it.
        return _fallback_draft(customer_name, contact_name, invoice_number, amount, due_date, days_overdue, stage)
