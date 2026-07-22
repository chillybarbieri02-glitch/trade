from datetime import date, datetime

import requests
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import ai_drafts, importer, oauth_store, sync
from .database import get_conn, init_db
from .integrations import oauth_state, quickbooks, xero
from .risk import compute_risk

app = FastAPI(title="CollectIQ - AI Accounts Receivable Assistant")

PROVIDERS = {"quickbooks": quickbooks, "xero": xero}


@app.on_event("startup")
def _startup():
    init_db()


def _invoice_view(row, conn) -> dict:
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (row["customer_id"],)).fetchone()
    due = datetime.strptime(row["due_date"], "%Y-%m-%d").date()
    risk = compute_risk(
        due_date=due,
        amount=row["amount"],
        historical_invoices=customer["historical_invoices"],
        historical_late=customer["historical_late"],
        reminders_sent=row["reminders_sent"],
    )
    return {
        "id": row["id"],
        "invoice_number": row["invoice_number"],
        "customer_id": customer["id"],
        "customer_name": customer["name"],
        "contact_name": customer["contact_name"],
        "amount": row["amount"],
        "issued_date": row["issued_date"],
        "due_date": row["due_date"],
        "status": row["status"],
        "reminders_sent": row["reminders_sent"],
        "risk_score": risk.score,
        "stage": risk.stage,
        "stage_label": risk.stage_label,
        "days_overdue": risk.days_overdue,
    }


@app.get("/api/invoices")
def list_invoices(status: str = "open"):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM invoices WHERE status = ? ORDER BY due_date ASC", (status,)
        ).fetchall()
        invoices = [_invoice_view(r, conn) for r in rows]
    invoices.sort(key=lambda v: v["risk_score"], reverse=True)
    return invoices


@app.get("/api/dashboard")
def dashboard():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM invoices WHERE status = 'open'").fetchall()
        views = [_invoice_view(r, conn) for r in rows]

    total_outstanding = sum(v["amount"] for v in views)
    at_risk = sum(v["amount"] for v in views if v["risk_score"] >= 50)
    overdue_count = sum(1 for v in views if v["days_overdue"] > 0)
    avg_days_late = (
        sum(v["days_overdue"] for v in views if v["days_overdue"] > 0) / overdue_count
        if overdue_count
        else 0
    )
    by_stage = {}
    for v in views:
        by_stage.setdefault(v["stage"], {"count": 0, "amount": 0.0})
        by_stage[v["stage"]]["count"] += 1
        by_stage[v["stage"]]["amount"] += v["amount"]

    return {
        "total_outstanding": round(total_outstanding, 2),
        "at_risk_amount": round(at_risk, 2),
        "overdue_count": overdue_count,
        "avg_days_late": round(avg_days_late, 1),
        "by_stage": by_stage,
    }


@app.post("/api/invoices/import")
async def upload_invoices(file: UploadFile):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")
    content = await file.read()
    try:
        result = importer.import_csv(content)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return result


@app.get("/api/integrations/status")
def integrations_status():
    result = {}
    for name, module in PROVIDERS.items():
        result[name] = {
            "configured": module.is_configured(),
            "connected": oauth_store.get_connection(name) is not None,
        }
    return result


@app.get("/api/integrations/{provider}/authorize")
def integrations_authorize(provider: str):
    module = PROVIDERS.get(provider)
    if not module:
        raise HTTPException(404, "Unknown provider")
    if not module.is_configured():
        raise HTTPException(
            400, f"{provider} is not configured - set its client id/secret/redirect env vars first"
        )
    return RedirectResponse(module.get_authorize_url())


@app.get("/api/integrations/quickbooks/callback")
def quickbooks_callback(code: str, state: str, realmId: str):
    if not oauth_state.consume(state):
        raise HTTPException(400, "Invalid or expired OAuth state")
    try:
        quickbooks.exchange_code(code, realmId)
    except requests.RequestException as exc:
        raise HTTPException(502, f"Could not reach QuickBooks: {exc}")
    return RedirectResponse("/?connected=quickbooks")


@app.get("/api/integrations/xero/callback")
def xero_callback(code: str, state: str):
    if not oauth_state.consume(state):
        raise HTTPException(400, "Invalid or expired OAuth state")
    try:
        xero.exchange_code(code)
    except requests.RequestException as exc:
        raise HTTPException(502, f"Could not reach Xero: {exc}")
    return RedirectResponse("/?connected=xero")


@app.post("/api/integrations/{provider}/sync")
def integrations_sync(provider: str):
    module = PROVIDERS.get(provider)
    if not module:
        raise HTTPException(404, "Unknown provider")
    try:
        records = module.fetch_open_invoice_records()
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))
    except requests.RequestException as exc:
        raise HTTPException(502, f"Could not reach {provider}: {exc}")
    return sync.upsert_records(records, update_existing=True)


@app.post("/api/integrations/{provider}/disconnect")
def integrations_disconnect(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Unknown provider")
    oauth_store.delete_connection(provider)
    return {"ok": True}


@app.post("/api/invoices/{invoice_id}/draft")
def draft_reminder(invoice_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Invoice not found")
        customer = conn.execute("SELECT * FROM customers WHERE id = ?", (row["customer_id"],)).fetchone()
        due = datetime.strptime(row["due_date"], "%Y-%m-%d").date()
        risk = compute_risk(
            due_date=due,
            amount=row["amount"],
            historical_invoices=customer["historical_invoices"],
            historical_late=customer["historical_late"],
            reminders_sent=row["reminders_sent"],
        )
        draft = ai_drafts.generate_draft(
            customer_name=customer["name"],
            contact_name=customer["contact_name"],
            invoice_number=row["invoice_number"],
            amount=row["amount"],
            due_date=row["due_date"],
            days_overdue=risk.days_overdue,
            stage=risk.stage,
        )
        conn.execute(
            "UPDATE invoices SET reminders_sent = reminders_sent + 1, last_stage = ? WHERE id = ?",
            (risk.stage, invoice_id),
        )
    return {"stage": risk.stage, "stage_label": risk.stage_label, "draft": draft}


@app.post("/api/invoices/{invoice_id}/mark_paid")
def mark_paid(invoice_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Invoice not found")
        due = datetime.strptime(row["due_date"], "%Y-%m-%d").date()
        was_late = date.today() > due
        conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
        conn.execute(
            "UPDATE customers SET historical_invoices = historical_invoices + 1, "
            "historical_late = historical_late + ? WHERE id = ?",
            (1 if was_late else 0, row["customer_id"]),
        )
    return {"ok": True}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
