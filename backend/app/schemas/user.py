from pydantic import BaseModel, Field


class LeadDaysUpdate(BaseModel):
    enabled: bool
    lead_days: list[int] = Field(default=[90, 30, 7, 1, 0])


class NotificationPrefOut(BaseModel):
    category: str
    enabled: bool
    lead_days: list[int]


class PrefsUpdateRequest(BaseModel):
    warranty: LeadDaysUpdate | None = None
    return_window: LeadDaysUpdate | None = None
    service: LeadDaysUpdate | None = None
    custom: LeadDaysUpdate | None = None


class PrefsResponse(BaseModel):
    preferences: list[NotificationPrefOut]


class DeviceTokenRequest(BaseModel):
    fcm_token: str = Field(min_length=10)
    platform: str = Field(default="unknown", max_length=20)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    profile_image_url: str | None = None