"""Xero OAuth + invoice sync.

Docs: https://developer.xero.com/documentation/api/accounting/invoices
OAuth: https://developer.xero.com/documentation/guides/oauth2/auth-flow

Network calls (exchange_code, refresh_access_token, fetch_open_invoice_records)
need a registered Xero app and are not covered by unit tests here - the
mapping logic they depend on (normalize_invoice) is pure and is tested
against sample Xero API payloads instead. Verify the network calls against a
Xero demo company before pointing this at production data.

Xero rotates refresh tokens on every use (the old one is invalidated the
moment a new one is issued), so the freshly returned refresh_token must
always be persisted - never reuse a previously stored one.
"""
import os
from urllib.parse import urlencode

import requests

from .. import oauth_store
from . import oauth_state

AUTH_URL = "https://login.xero.com/identity/connect/authorize"
TOKEN_URL = "https://identity.xero.com/connect/token"
CONNECTIONS_URL = "https://api.xero.com/connections"
API_BASE = "https://api.xero.com/api.xro/2.0"
SCOPE = "accounting.transactions accounting.contacts offline_access"
PROVIDER = "xero"


def _client_id():
    return os.environ.get("XERO_CLIENT_ID")


def _client_secret():
    return os.environ.get("XERO_CLIENT_SECRET")


def _redirect_uri():
    return os.environ.get("XERO_REDIRECT_URI")


def is_configured() -> bool:
    return bool(_client_id() and _client_secret() and _redirect_uri())


def get_authorize_url() -> str:
    params = {
        "response_type": "code",
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "scope": SCOPE,
        "state": oauth_state.issue(),
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _fetch_tenant_id(access_token: str) -> str:
    response = requests.get(CONNECTIONS_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
    response.raise_for_status()
    connections = response.json()
    if not connections:
        raise RuntimeError("Xero authorized but no organisation connection was returned")
    return connections[0]["tenantId"]


def exchange_code(code: str) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": _redirect_uri()},
        auth=(_client_id(), _client_secret()),
        timeout=15,
    )
    response.raise_for_status()
    tokens = response.json()
    tenant_id = _fetch_tenant_id(tokens["access_token"])
    oauth_store.save_connection(PROVIDER, tokens["access_token"], tokens["refresh_token"], tokens["expires_in"], tenant_id)
    return tokens


def refresh_access_token(connection: dict) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": connection["refresh_token"]},
        auth=(_client_id(), _client_secret()),
        timeout=15,
    )
    response.raise_for_status()
    tokens = response.json()
    oauth_store.save_connection(
        PROVIDER, tokens["access_token"], tokens["refresh_token"], tokens["expires_in"], connection["tenant_id"]
    )
    return tokens


def get_valid_access_token() -> tuple[str, str]:
    connection = oauth_store.get_connection(PROVIDER)
    if not connection:
        raise RuntimeError("Xero is not connected")
    if oauth_store.is_expired(connection):
        connection = {**connection, **refresh_access_token(connection)}
    return connection["access_token"], connection["tenant_id"]


def normalize_invoice(raw_invoice: dict) -> dict | None:
    """raw_invoice: one Xero Invoice entity (Contact is embedded, no lookup needed)."""
    amount_due = raw_invoice.get("AmountDue", 0)
    if not amount_due:
        return None

    contact = raw_invoice.get("Contact", {})
    due_date = (raw_invoice.get("DueDateString") or "")[:10] or None
    issued_date = (raw_invoice.get("DateString") or "")[:10] or due_date

    return {
        "customer_name": contact.get("Name") or "Unknown customer",
        "contact_name": None,
        "email": contact.get("EmailAddress"),
        "invoice_number": raw_invoice.get("InvoiceNumber") or f"XERO-{raw_invoice.get('InvoiceID')}",
        "amount": float(amount_due),
        "issued_date": issued_date,
        "due_date": due_date,
        "paid": False,
    }


def fetch_open_invoice_records() -> list[dict]:
    access_token, tenant_id = get_valid_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Xero-tenant-id": tenant_id,
        "Accept": "application/json",
    }
    response = requests.get(
        f"{API_BASE}/Invoices",
        params={"Statuses": "AUTHORISED", "where": 'Type=="ACCREC"'},
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    raw_invoices = response.json().get("Invoices", [])
    records = [normalize_invoice(inv) for inv in raw_invoices]
    return [r for r in records if r]
