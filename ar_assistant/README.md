# CollectIQ - AI Accounts Receivable Assistant

Small businesses lose a meaningful share of revenue to late-paying
customers, but almost all AI investment in the SMB software space goes
toward sales and marketing (chatbots, ad copy, lead scoring). Getting paid
for work already delivered gets comparatively little AI tooling, even
though it has a more direct and measurable effect on cash flow. CollectIQ
targets that gap: it ranks open invoices by collection risk and drafts the
next reminder email at the right tone for how overdue it is.

## What it does

1. **Pulls invoices from QuickBooks Online or Xero** via OAuth, or accepts
   a CSV for any other source. Syncing re-checks balances each time, so a
   partially-paid invoice or one paid off entirely updates automatically.
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

Open http://127.0.0.1:8000. If QuickBooks or Xero is configured (see below)
you'll see a "Connect" button for it; otherwise use "Or import a CSV" to
load `sample_data/invoices_sample.csv` for a demo, or your own file with
these columns: `customer_name, contact_name, email, invoice_number, amount,
issued_date, due_date` (dates as `YYYY-MM-DD`).

## Enabling AI-drafted reminders

Set both `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in `.env` (use whichever
current Claude model your account has access to). Without both set,
"Draft reminder" still works, using deterministic templates instead of a
live model call - useful for demos or offline use.

## Connecting QuickBooks or Xero

Both replace the manual CSV step with a one-click "Connect" + "Sync now",
and keep pulling current balances on every sync (so paid-down or
fully-paid invoices update instead of piling up as stale rows). Either can
be enabled independently; CSV import keeps working regardless, for sources
that aren't QuickBooks or Xero.

**QuickBooks Online**
1. Create an app at https://developer.intuit.com/app/developer/qbo - the
   Development tab gives you a free sandbox company to test against before
   touching real data.
2. Set its redirect URI to `http://localhost:8000/api/integrations/quickbooks/callback`
   (or your real host, if not running locally).
3. In `.env`, set `QUICKBOOKS_CLIENT_ID`, `QUICKBOOKS_CLIENT_SECRET`,
   `QUICKBOOKS_REDIRECT_URI` (matching exactly what you registered), and
   `QUICKBOOKS_ENVIRONMENT` (`sandbox` or `production`).
4. Restart the app, click "Connect QuickBooks", authorize, and it syncs
   automatically on the first connection.

**Xero**
1. Create an app at https://developer.xero.com/app/manage.
2. Set its redirect URI to `http://localhost:8000/api/integrations/xero/callback`.
3. In `.env`, set `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `XERO_REDIRECT_URI`.
4. Restart the app, click "Connect Xero", authorize, and it syncs
   automatically on the first connection.

Only invoices with a remaining balance are pulled in (QuickBooks: `Balance
> 0`; Xero: `AmountDue > 0` on `AUTHORISED` invoices), matching the "open"
invoices this app is meant to chase. The OAuth exchange and API calls
(`app/integrations/quickbooks.py`, `app/integrations/xero.py`) need a real
registered app to exercise end-to-end - they haven't been run against a
live sandbox here, so treat the network calls as implemented-to-spec
rather than verified, and check them against your sandbox before trusting
them with production data. The field-mapping logic they depend on
(`normalize_invoice` in each module) is unit-tested against sample
QuickBooks/Xero API payloads.

## Project layout

```
app/
  main.py           FastAPI routes
  database.py       SQLite schema + connection helper
  risk.py           Collection-risk scoring and stage assignment
  ai_drafts.py      AI (or template-fallback) email drafting
  importer.py       CSV -> customers/invoices (via sync.py)
  sync.py           Shared upsert logic used by CSV import and OAuth sync
  oauth_store.py    Persists QuickBooks/Xero OAuth tokens
  integrations/
    oauth_state.py  CSRF state tokens for the OAuth round trip
    quickbooks.py   QuickBooks OAuth + invoice sync
    xero.py         Xero OAuth + invoice sync
static/             Single-page dashboard (vanilla HTML/JS, no build step)
sample_data/        Example invoice CSV for a demo
tests/              pytest suite for risk scoring, CSV import, sync, and
                     QuickBooks/Xero field mapping
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
