# CollectIQ - AI Accounts Receivable Assistant

Small businesses lose a meaningful share of revenue to late-paying
customers, but almost all AI investment in the SMB software space goes
toward sales and marketing (chatbots, ad copy, lead scoring). Getting paid
for work already delivered gets comparatively little AI tooling, even
though it has a more direct and measurable effect on cash flow. CollectIQ
targets that gap: it ranks open invoices by collection risk and drafts the
next reminder email at the right tone for how overdue it is.

## What it does

1. **Import invoices** from a CSV (customer, invoice number, amount, issued
   date, due date).
2. **Risk-scores every open invoice** (0-100) from days overdue, invoice
   size, the customer's history of paying late, and how many reminders
   have already gone unanswered - then sorts the worklist by that score.
3. **Assigns a collection stage** per invoice - not due, friendly reminder,
   firm follow-up, final notice, escalate - based on days overdue.
4. **Drafts the reminder email with AI**, matching tone to the stage
   (warm for a first reminder, unambiguous for a final notice), using the
   Anthropic API when configured. Falls back to a clear template
   automatically if no API key is set, so the app is fully usable without
   one.
5. **Dashboard** showing total outstanding, dollars at risk, overdue count,
   and average days late.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: fill in ANTHROPIC_API_KEY + ANTHROPIC_MODEL for AI drafts
export $(grep -v '^#' .env | xargs)   # skip this line if you left .env empty
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000, then use "Import invoices (CSV)" to load
`sample_data/invoices_sample.csv` for a demo, or your own file with these
columns: `customer_name, contact_name, email, invoice_number, amount,
issued_date, due_date` (dates as `YYYY-MM-DD`).

## Enabling AI-drafted reminders

Set both `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in `.env` (use whichever
current Claude model your account has access to). Without both set,
"Draft reminder" still works, using deterministic templates instead of a
live model call - useful for demos or offline use.

## Project layout

```
app/
  main.py        FastAPI routes
  database.py    SQLite schema + connection helper
  risk.py        Collection-risk scoring and stage assignment
  ai_drafts.py   AI (or template-fallback) email drafting
  importer.py    CSV -> customers/invoices
static/          Single-page dashboard (vanilla HTML/JS, no build step)
sample_data/     Example invoice CSV for a demo
tests/           pytest suite for risk scoring and CSV import
```

## Tests

```bash
pytest
```

## Notes on scope

This is a working single-tenant prototype (SQLite, no auth) meant to prove
out the product idea end-to-end - not a production multi-tenant system.
The obvious next steps would be per-business accounts, real email sending
(vs. copy-to-clipboard drafts), and a scheduler that auto-advances stages
and surfaces the daily worklist without a manual refresh.
