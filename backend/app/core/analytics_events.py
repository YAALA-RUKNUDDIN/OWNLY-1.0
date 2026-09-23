"""Analytics event catalog.

Event names are part of the contract consumed by the mobile app's funnel
dashboards; keep them stable and additive (never rename — deprecate).
"""
from enum import Enum


class AnalyticsEvent(str, Enum):
    user_registered = "user_registered"
    user_logged_in = "user_logged_in"
    product_added = "product_added"
    product_deleted = "product_deleted"
    document_uploaded = "document_uploaded"
    ocr_extracted = "ocr_extracted"
    warranty_added = "warranty_added"
    reminder_created = "reminder_created"
    today_viewed = "today_viewed"
    export_requested = "export_requested"
    account_deleted = "account_deleted"
    subscription_activated = "subscription_activated"
    subscription_canceled = "subscription_canceled"
    notification_sent = "notification_sent"
