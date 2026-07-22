from app import oauth_store


def test_save_and_get_connection_round_trips(isolated_db):
    oauth_store.save_connection("quickbooks", "access-1", "refresh-1", 3600, "realm-1")
    connection = oauth_store.get_connection("quickbooks")
    assert connection["access_token"] == "access-1"
    assert connection["refresh_token"] == "refresh-1"
    assert connection["tenant_id"] == "realm-1"


def test_missing_connection_returns_none(isolated_db):
    assert oauth_store.get_connection("quickbooks") is None


def test_saving_again_overwrites_the_same_provider_row(isolated_db):
    oauth_store.save_connection("xero", "access-1", "refresh-1", 3600, "tenant-1")
    oauth_store.save_connection("xero", "access-2", "refresh-2", 1800, "tenant-1")
    connection = oauth_store.get_connection("xero")
    assert connection["access_token"] == "access-2"
    assert connection["refresh_token"] == "refresh-2"


def test_is_expired_true_for_past_expiry(isolated_db):
    oauth_store.save_connection("xero", "access-1", "refresh-1", -10, "tenant-1")
    connection = oauth_store.get_connection("xero")
    assert oauth_store.is_expired(connection) is True


def test_is_expired_false_for_future_expiry(isolated_db):
    oauth_store.save_connection("xero", "access-1", "refresh-1", 3600, "tenant-1")
    connection = oauth_store.get_connection("xero")
    assert oauth_store.is_expired(connection) is False


def test_delete_connection_removes_row(isolated_db):
    oauth_store.save_connection("xero", "access-1", "refresh-1", 3600, "tenant-1")
    oauth_store.delete_connection("xero")
    assert oauth_store.get_connection("xero") is None
