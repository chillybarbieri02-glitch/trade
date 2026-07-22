from datetime import date, timedelta

from app.risk import compute_risk, stage_for_days_overdue


def test_not_yet_due_has_zero_days_overdue_and_low_risk():
    due = date.today() + timedelta(days=5)
    result = compute_risk(due_date=due, amount=1000, historical_invoices=0, historical_late=0, reminders_sent=0)
    assert result.days_overdue == 0
    assert result.stage == "not_due"
    assert result.score < 10


def test_risk_increases_with_days_overdue():
    today = date.today()
    mild = compute_risk(due_date=today - timedelta(days=10), amount=1000, historical_invoices=0, historical_late=0, reminders_sent=0)
    severe = compute_risk(due_date=today - timedelta(days=70), amount=1000, historical_invoices=0, historical_late=0, reminders_sent=0)
    assert severe.score > mild.score
    assert severe.stage == "escalate"


def test_customer_late_history_raises_score():
    due = date.today() - timedelta(days=10)
    clean_history = compute_risk(due_date=due, amount=1000, historical_invoices=10, historical_late=0, reminders_sent=0)
    bad_history = compute_risk(due_date=due, amount=1000, historical_invoices=10, historical_late=8, reminders_sent=0)
    assert bad_history.score > clean_history.score


def test_stage_thresholds():
    assert stage_for_days_overdue(0)[0] == "not_due"
    assert stage_for_days_overdue(10)[0] == "friendly"
    assert stage_for_days_overdue(20)[0] == "firm"
    assert stage_for_days_overdue(45)[0] == "final"
    assert stage_for_days_overdue(90)[0] == "escalate"


def test_score_never_exceeds_bounds():
    due = date.today() - timedelta(days=400)
    result = compute_risk(due_date=due, amount=1_000_000, historical_invoices=5, historical_late=5, reminders_sent=20)
    assert 0 <= result.score <= 100
