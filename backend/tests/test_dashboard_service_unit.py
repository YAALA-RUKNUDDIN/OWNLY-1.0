"""Unit tests for TodayService pure classifiers — no database involved.

These pin the priority/bucket rules that power the Today screen:
  - 14-day warranty  → attention (spec example)
  - expired return window → invisible (nothing actionable)
  - overdue service  → critical
  - severity ordering guarantees the Today screen's urgency sort
"""
from datetime import date, datetime, timedelta

from app.services.dashboard_service import (
    classify_reminder,
    classify_return,
    classify_service,
    classify_warranty,
    build_greeting,
)

TODAY = date(2026, 9, 23)


def d(days_from_today):
    return TODAY.fromordinal(TODAY.toordinal() + days_from_today)


class TestWarrantyClassification:
    def test_spec_example_14_days_is_attention(self):
        bucket, kind, severity, days, _ = classify_warranty(d(14), TODAY)
        assert (bucket, kind, severity) == ("attention", "warranty_expiring", "warning")
        assert days == 14

    def test_7_days_is_critical(self):
        _, _, severity, days, _ = classify_warranty(d(7), TODAY)
        assert (severity, days) == ("critical", 7)

    def test_31_days_moves_to_upcoming(self):
        bucket, kind, severity, days, _ = classify_warranty(d(31), TODAY)
        assert (bucket, severity) == ("upcoming", "info")

    def test_expired_within_grace_is_attention_info(self):
        bucket, kind, severity, days, _ = classify_warranty(d(-5), TODAY)
        assert (bucket, kind, severity, days) == ("attention", "warranty_expired", "info", -5)

    def test_long_expired_is_dropped(self):
        assert classify_warranty(d(-31), TODAY) is None

    def test_accepts_datetime(self):
        bucket, _, _, days, _ = classify_warranty(datetime(2026, 10, 7, 12, 0), TODAY)
        assert bucket == "attention" and days == 14


class TestReturnClassification:
    def test_last_day_is_critical(self):
        bucket, kind, severity, days, _ = classify_return(d(-1), 1, TODAY)  # bought yesterday, 1-day window
        assert (bucket, kind, severity) == ("attention", "return_expiring", "critical")

    def test_closed_window_is_invisible(self):
        assert classify_return(d(-10), 5, TODAY) is None

    def test_no_tracking_is_invisible(self):
        assert classify_return(d(0), 0, TODAY) is None
        assert classify_return(d(0), None, TODAY) is None

    def test_outside_horizon_is_dropped(self):
        assert classify_return(d(0), 200, TODAY) is None


class TestServiceClassification:
    def test_overdue_is_critical_attention(self):
        bucket, kind, severity, days, _ = classify_service(d(-3), TODAY)
        assert (bucket, kind, severity, days) == ("attention", "service_due", "critical", -3)

    def test_far_out_is_upcoming(self):
        bucket, _, severity, _, _ = classify_service(d(60), TODAY)
        assert (bucket, severity) == ("upcoming", "info")


class TestReminderClassification:
    def test_due_today_is_attention(self):
        bucket, kind, severity, days, _ = classify_reminder(TODAY, TODAY)
        assert (bucket, kind, severity, days) == ("attention", "reminder_due", "critical", 0)

    def test_8_days_out_is_upcoming(self):
        bucket, _, _, days, _ = classify_reminder(d(8), TODAY)
        assert (bucket, days) == ("upcoming", 8)


class TestGreeting:
    def test_time_based(self):
        assert build_greeting(9, "Ada Lovelace") == "Good morning, Ada"
        assert build_greeting(14, "Ada") == "Good afternoon, Ada"
        assert build_greeting(21, "Ada") == "Good evening, Ada"

    def test_no_name(self):
        assert build_greeting(9, None) == "Good morning"
