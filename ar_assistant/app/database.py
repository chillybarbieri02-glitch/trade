"""SQLite storage for customers and invoices. Plain sqlite3 - no ORM needed at this scale."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("COLLECTIQ_DB_PATH", "collectiq.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    historical_invoices INTEGER NOT NULL DEFAULT 0,
    historical_late INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    invoice_number TEXT NOT NULL,
    amount REAL NOT NULL,
    issued_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    reminders_sent INTEGER NOT NULL DEFAULT 0,
    last_stage TEXT NOT NULL DEFAULT 'not_due'
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def reset_db():
    """Used by tests to start from a clean slate."""
    with get_conn() as conn:
        conn.executescript("DROP TABLE IF EXISTS invoices; DROP TABLE IF EXISTS customers;")
        conn.executescript(SCHEMA)
