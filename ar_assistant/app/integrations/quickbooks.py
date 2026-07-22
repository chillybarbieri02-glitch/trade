"""QuickBooks Online OAuth + invoice sync.

Docs: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/invoice
OAuth: https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0

Network calls (exchange_code, refresh_access_token, fetch_open_invoice_records)
need a registered Intuit app and are not covered by unit tests here - the
mapping logic they depend on (normalize_invoice) is pure and is tested
against sample QBO API payloads instead. Verify the network calls against a
QuickBooks sandbox company before pointing this at production data.
"""
import os
from urllib.parse import urlencode

import requests

from .. import oauth_store
from . import oauth_state

AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
SCOPE = "com.intuit.quickbooks.accounting"
PROVIDER = "quickbooks"


def _client_id():
    return os.environ.get("QUICKBOOKS_CLIENT_ID")


def _client_secret():
    return os.environ.get("QUICKBOOKS_CLIENT_SECRET")


def _redirect_uri():
    return os.environ.get("QUICKBOOKS_REDIRECT_URI")


def _api_base():
    env = os.environ.get("QUICKBOOKS_ENVIRONMENT", "sandbox")
    host = "quickbooks.api.intuit.com" if env == "production" else "sandbox-quickbooks.api.intuit.com"
    return f"https://{host}"


def is_configured() -> bool:
    return bool(_client_id() and _client_secret() and _redirect_uri())


def get_authorize_url() -> str:
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": SCOPE,
        "state": oauth_state.issue(),
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str, realm_id: str) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": _redirect_uri()},
        auth=(_client_id(), _client_secret()),
        headers={"Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    tokens = response.json()
    oauth_store.save_connection(
        PROVIDER, tokens["access_token"], tokens["refresh_token"], tokens["expires_in"], realm_id
    )
    return tokens


def refresh_access_token(connection: dict) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": connection["refresh_token"]},
        auth=(_client_id(), _client_secret()),
        headers={"Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    tokens = response.json()
    oauth_store.save_connection(
        PROVIDER,
        tokens["access_token"],
        tokens.get("refresh_token", connection["refresh_token"]),
        tokens["expires_in"],
        connection["tenant_id"],
    )
    return tokens


def get_valid_access_token() -> tuple[str, str]:
    connection = oauth_store.get_connection(PROVIDER)
    if not connection:
        raise RuntimeError("QuickBooks is not connected")
    if oauth_store.is_expired(connection):
        connection = {**connection, **refresh_access_token(connection)}
    return connection["access_token"], connection["tenant_id"]


def normalize_invoice(raw_invoice: dict, customer_lookup: dict) -> dict | None:
    """raw_invoice: one QBO Invoice entity. customer_lookup: {customer_id: {"name":..., "email":...}}."""
    balance = raw_invoice.get("Balance", 0)
    if not balance:
        return None

    customer_ref = raw_invoice.get("CustomerRef", {})
    customer = customer_lookup.get(customer_ref.get("value"), {})
    customer_name = customer.get("name") or customer_ref.get("name") or "Unknown customer"

    return {
        "customer_name": customer_name,
        "contact_name": None,
        "email": customer.get("email"),
        "invoice_number": raw_invoice.get("DocNumber") or f"QBO-{raw_invoice.get('Id')}",
        "amount": float(balance),
        "issued_date": raw_invoice.get("TxnDate"),
        "due_date": raw_invoice.get("DueDate") or raw_invoice.get("TxnDate"),
        "paid": False,
    }


def fetch_open_invoice_records() -> list[dict]:
    access_token, realm_id = get_valid_access_token()
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    base = f"{_api_base()}/v3/company/{realm_id}"

    customers_resp = requests.get(
        f"{base}/query", params={"query": "SELECT * FROM Customer MAXRESULTS 1000"}, headers=headers, timeout=20
    )
    customers_resp.raise_for_status()
    customers = customers_resp.json().get("QueryResponse", {}).get("Customer", [])
    customer_lookup = {
        c["Id"]: {"name": c.get("DisplayName"), "email": (c.get("PrimaryEmailAddr") or {}).get("Address")}
        for c in customers
    }

    invoices_resp = requests.get(
        f"{base}/query",
        params={"query": "SELECT * FROM Invoice WHERE Balance > '0' MAXRESULTS 1000"},
        headers=headers,
        timeout=20,
    )
    invoices_resp.raise_for_status()
    raw_invoices = invoices_resp.json().get("QueryResponse", {}).get("Invoice", [])

    records = [normalize_invoice(inv, customer_lookup) for inv in raw_invoices]
    return [r for r in records if r]
