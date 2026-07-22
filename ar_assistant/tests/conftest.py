import os

import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLECTIQ_DB_PATH", str(tmp_path / "test.db"))
    import importlib

    from app import database

    importlib.reload(database)
    database.init_db()
    yield database
