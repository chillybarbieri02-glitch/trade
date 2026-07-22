"""Collection-risk scoring and reminder-stage assignment for a single invoice.

Score is 0-100. Higher means: more overdue, larger balance, and/or a customer
with a track record of paying late. Stage determines which tone of reminder
the AI should draft next.
"""
from dataclasses import dataclass
from datetime import date, datetime


STAGE_THRESHOLDS = (
    # (max_days_overdue, stage, label)
    (0, "not_due", "Not yet due"),
    (15, "friendly", "Friendly reminder"),
    (30, "firm", "Firm follow-up"),
    (60, "final", "Final notice"),
    (float("inf"), "escalate", "Escalate / collections"),
)


def days_overdue(due_date: date, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    return max(0, (as_of - due_date).days)


def stage_for_days_overdue(overdue: int) -> tuple[str, str]:
    for max_days, stage, label in STAGE_THRESHOLDS:
        if overdue <= max_days:
            return stage, label
    return "escalate", "Escalate / collections"


@dataclass
class RiskResult:
    score: int
    stage: str
    stage_label: str
    days_overdue: int


def compute_risk(
    due_date: date,
    amount: float,
    historical_invoices: int,
    historical_late: int,
    reminders_sent: int,
    as_of: date | None = None,
) -> RiskResult:
    overdue = days_overdue(due_date, as_of)
    stage, stage_label = stage_for_days_overdue(overdue)

    late_ratio = (historical_late / historical_invoices) if historical_invoices else 0.0

    overdue_component = min(60, overdue * 1.2)
    history_component = late_ratio * 25
    persistence_component = min(10, reminders_sent * 3)
    size_component = min(5, amount / 2000)

    score = round(overdue_component + history_component + persistence_component + size_component)
    score = max(0, min(100, score))

    return RiskResult(score=score, stage=stage, stage_label=stage_label, days_overdue=overdue)
