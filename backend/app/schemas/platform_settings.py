"""Schemas for platform settings."""

from uuid import UUID

from pydantic import BaseModel, Field


class GeneralSettings(BaseModel):
    """General platform settings."""

    platform_name: str = Field(default="Exam Prep Platform", max_length=80)
    platform_description: str = Field(default="", max_length=500)
    default_language: str = Field(default="en")
    timezone: str = Field(default="Asia/Karachi")
    default_landing: str = Field(default="dashboard")  # dashboard | blocks | analytics


class AcademicDefaults(BaseModel):
    """Academic default settings."""

    default_year_id: int | None = None
    blocks_visibility_mode: str = Field(default="user_selected")  # user_selected | all


class PracticeDefaults(BaseModel):
    """Practice default settings (self-paced)."""

    default_mode: str = Field(default="tutor")  # tutor | exam
    timer_default: str = Field(default="untimed")  # untimed | timed
    review_policy: str = Field(default="always")  # always | after_submit | never
    allow_mixed_blocks: bool = Field(default=True)
    allow_any_block_anytime: bool = Field(default=True)


class SecuritySettings(BaseModel):
    """Security settings."""

    access_token_minutes: int = Field(default=30, ge=5, le=240)
    refresh_token_days: int = Field(default=14, ge=1, le=90)
    force_logout_on_password_reset: bool = Field(default=True)


class NotificationSettings(BaseModel):
    """Notification settings."""

    password_reset_emails_enabled: bool = Field(default=True)
    practice_reminders_enabled: bool = Field(default=False)
    admin_alerts_enabled: bool = Field(default=False)
    inapp_announcements_enabled: bool = Field(default=True)


class PlatformSettingsData(BaseModel):
    """Complete platform settings schema."""

    general: GeneralSettings = Field(default_factory=GeneralSettings)
    academic_defaults: AcademicDefaults = Field(default_factory=AcademicDefaults)
    practice_defaults: PracticeDefaults = Field(default_factory=PracticeDefaults)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    version: int = Field(default=1)


class PlatformSettingsResponse(BaseModel):
    """Response schema for platform settings."""

    data: PlatformSettingsData
    updated_at: str | None = None
    updated_by_user_id: UUID | None = None


class PlatformSettingsUpdate(BaseModel):
    """Update schema for platform settings."""

    data: PlatformSettingsData
