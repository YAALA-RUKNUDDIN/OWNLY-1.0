"""Analytics + monitoring abstractions (Phase 2).

The contract under test: event catalog is stable, the factory honours the
setting, and an analytics failure can never break a request.
"""
from app.core.analytics_events import AnalyticsEvent
from app.core.config import settings
from app.integrations import analytics
from app.integrations.analytics.base import AnalyticsProvider
from app.integrations.analytics.noop import NoopAnalyticsProvider
from app.integrations.monitoring import init_sentry


class TestAnalytics:
    def test_noop_provider_is_silent_and_safe(self):
        NoopAnalyticsProvider().track("some_event", None, {"a": 1})

    def test_factory_honours_setting(self, monkeypatch):
        monkeypatch.setattr(settings, "ANALYTICS_PROVIDER", "noop")
        analytics.get_analytics.cache_clear()
        assert analytics.get_analytics().name == "noop"

        monkeypatch.setattr(settings, "ANALYTICS_PROVIDER", "log")
        analytics.get_analytics.cache_clear()
        assert analytics.get_analytics().name == "log"
        analytics.get_analytics.cache_clear()

    def test_track_never_raises_when_sink_fails(self, monkeypatch):
        class BrokenProvider(AnalyticsProvider):
            name = "broken"

            def track(self, event, user_id=None, properties=None):
                raise RuntimeError("sink unavailable")

        monkeypatch.setattr(analytics, "get_analytics", lambda: BrokenProvider())
        analytics.track(AnalyticsEvent.product_added, None, {"x": 1})  # must not raise

    def test_track_accepts_enum_and_plain_string(self, monkeypatch):
        seen: list[str] = []

        class Recorder(AnalyticsProvider):
            name = "recorder"

            def track(self, event, user_id=None, properties=None):
                seen.append(event)

        monkeypatch.setattr(analytics, "get_analytics", lambda: Recorder())
        analytics.track(AnalyticsEvent.today_viewed)
        analytics.track("custom_event")
        assert seen == ["today_viewed", "custom_event"]

    def test_event_catalog_is_unique_lowercase_snake_case(self):
        values = [e.value for e in AnalyticsEvent]
        assert len(values) == len(set(values))
        assert all(v == v.lower() and " " not in v for v in values)


class TestSentry:
    def test_disabled_without_dsn(self, monkeypatch):
        monkeypatch.setattr(settings, "SENTRY_DSN", "")
        init_sentry.cache_clear()
        assert init_sentry() is False
        init_sentry.cache_clear()

    def test_missing_sdk_degrades_to_noop(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("sentry_sdk"):
                raise ImportError("sentry-sdk not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(settings, "SENTRY_DSN", "https://example.invalid/1")
        monkeypatch.setattr(builtins, "__import__", fake_import)
        init_sentry.cache_clear()
        assert init_sentry() is False
        init_sentry.cache_clear()
