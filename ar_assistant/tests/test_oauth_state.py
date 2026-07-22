from app.integrations import oauth_state


def test_issued_token_is_consumed_exactly_once():
    token = oauth_state.issue()
    assert oauth_state.consume(token) is True
    assert oauth_state.consume(token) is False


def test_unknown_token_is_rejected():
    assert oauth_state.consume("never-issued") is False


def test_expired_token_is_rejected(monkeypatch):
    token = oauth_state.issue()
    import time as time_module

    future = time_module.time() + 10_000
    monkeypatch.setattr(time_module, "time", lambda: future)
    assert oauth_state.consume(token) is False
