from urllib.parse import parse_qs, urlparse

from app.integrations import quickbooks, xero


def test_quickbooks_not_configured_without_env(monkeypatch):
    monkeypatch.delenv("QUICKBOOKS_CLIENT_ID", raising=False)
    monkeypatch.delenv("QUICKBOOKS_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("QUICKBOOKS_REDIRECT_URI", raising=False)
    assert quickbooks.is_configured() is False


def test_quickbooks_configured_with_all_three_env_vars(monkeypatch):
    monkeypatch.setenv("QUICKBOOKS_CLIENT_ID", "id")
    monkeypatch.setenv("QUICKBOOKS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("QUICKBOOKS_REDIRECT_URI", "https://example.com/callback")
    assert quickbooks.is_configured() is True


def test_quickbooks_authorize_url_includes_required_params(monkeypatch):
    monkeypatch.setenv("QUICKBOOKS_CLIENT_ID", "my-id")
    monkeypatch.setenv("QUICKBOOKS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("QUICKBOOKS_REDIRECT_URI", "https://example.com/callback")
    url = quickbooks.get_authorize_url()
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.netloc == "appcenter.intuit.com"
    assert params["client_id"] == ["my-id"]
    assert params["redirect_uri"] == ["https://example.com/callback"]
    assert params["scope"] == ["com.intuit.quickbooks.accounting"]
    assert len(params["state"][0]) > 10


def test_xero_authorize_url_includes_required_params(monkeypatch):
    monkeypatch.setenv("XERO_CLIENT_ID", "my-id")
    monkeypatch.setenv("XERO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("XERO_REDIRECT_URI", "https://example.com/callback")
    url = xero.get_authorize_url()
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.netloc == "login.xero.com"
    assert params["client_id"] == ["my-id"]
    assert "offline_access" in params["scope"][0]
