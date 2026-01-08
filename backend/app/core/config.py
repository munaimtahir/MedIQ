"""Application settings and configuration."""

from typing import Literal

from pydantic import Field, field_validator, model_validator  # type: ignore
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    ENV: Literal["dev", "staging", "prod", "test"] = Field(default="dev")
    PROJECT_NAME: str = Field(default="Medical Exam Platform API")

    # API
    API_PREFIX: str = Field(default="/v1")
    API_V1_STR: str = Field(default="/v1")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://exam_user:change_me@localhost:5432/exam_platform"
    )

    # Redis
    REDIS_URL: str | None = Field(default=None)
    REDIS_ENABLED: bool = Field(default=True)
    REDIS_REQUIRED: bool = Field(default=False)  # True in prod, False in dev

    # CORS - Accept string or list, will be normalized to list
    CORS_ORIGINS: str | list[str] = Field(default="http://localhost:3000,http://localhost:3001")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    # Security - JWT
    JWT_SECRET: str | None = Field(default=None)
    JWT_ALG: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14)
    TOKEN_PEPPER: str | None = Field(default=None)  # Server-side pepper for token hashing

    # Password Reset
    PASSWORD_RESET_EXPIRE_MINUTES: int = Field(default=30)

    # Seeding
    SEED_DEMO_ACCOUNTS: bool = Field(default=False)

    # OAuth/OIDC
    OAUTH_GOOGLE_CLIENT_ID: str | None = Field(default=None)
    OAUTH_GOOGLE_CLIENT_SECRET: str | None = Field(default=None)
    OAUTH_GOOGLE_REDIRECT_URI: str | None = Field(default=None)
    OAUTH_MICROSOFT_CLIENT_ID: str | None = Field(default=None)
    OAUTH_MICROSOFT_CLIENT_SECRET: str | None = Field(default=None)
    OAUTH_MICROSOFT_REDIRECT_URI: str | None = Field(default=None)
    OAUTH_MICROSOFT_TENANT: str = Field(default="common")  # Azure AD tenant
    OAUTH_STATE_TTL: int = Field(default=600)  # 10 minutes
    OAUTH_NONCE_TTL: int = Field(default=600)  # 10 minutes
    OAUTH_LINK_TTL: int = Field(default=600)  # 10 minutes for link tokens
    OAUTH_TOKEN_CODE_TTL: int = Field(default=60)  # 60 seconds for OAuth token exchange codes
    JWKS_CACHE_TTL_SECONDS: int = Field(default=3600)  # 1 hour
    OAUTH_ALLOWED_REDIRECT_URIS: str | None = Field(
        default=None
    )  # Comma-separated list of allowed redirect URIs

    # Frontend URL for OAuth redirects
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    FRONTEND_BASE_URL: str = Field(default="http://localhost:3000")  # For password reset links
    EMAIL_VERIFY_PATH: str = Field(default="/verify-email")
    RESET_PASSWORD_PATH: str = Field(default="/reset-password")

    # Email verification
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = Field(default=1440)  # 24 hours

    # Email Configuration
    EMAIL_BACKEND: str = Field(default="console")  # console, mailpit, smtp
    EMAIL_HOST: str = Field(default="localhost")
    EMAIL_PORT: int = Field(default=1025)
    EMAIL_FROM: str = Field(default="noreply@local.test")
    EMAIL_USE_TLS: bool = Field(default=False)
    EMAIL_USE_SSL: bool = Field(default=False)

    # MFA
    MFA_ENCRYPTION_KEY: str | None = Field(default=None)  # Fernet key for encrypting TOTP secrets
    MFA_TOTP_ISSUER: str = Field(default="ExamPrepSite")
    MFA_TOTP_PERIOD: int = Field(default=30)
    MFA_TOTP_DIGITS: int = Field(default=6)
    MFA_BACKUP_CODES_COUNT: int = Field(default=10)
    MFA_TOKEN_EXPIRE_MINUTES: int = Field(default=5)  # MFA pending token TTL

    # Rate Limiting
    RL_LOGIN_IP_LIMIT: int = Field(default=20)
    RL_LOGIN_IP_WINDOW: int = Field(default=600)  # 10 minutes
    RL_LOGIN_EMAIL_LIMIT: int = Field(default=10)
    RL_LOGIN_EMAIL_WINDOW: int = Field(default=600)  # 10 minutes
    RL_SIGNUP_IP_LIMIT: int = Field(default=5)
    RL_SIGNUP_IP_WINDOW: int = Field(default=3600)  # 1 hour
    RL_RESET_IP_LIMIT: int = Field(default=5)
    RL_RESET_IP_WINDOW: int = Field(default=3600)  # 1 hour
    RL_RESET_EMAIL_LIMIT: int = Field(default=3)
    RL_RESET_EMAIL_WINDOW: int = Field(default=3600)  # 1 hour
    RL_REFRESH_USER_LIMIT: int = Field(default=60)
    RL_REFRESH_USER_WINDOW: int = Field(default=3600)  # 1 hour

    # Brute-force Protection
    LOGIN_FAIL_EMAIL_THRESHOLD: int = Field(default=8)
    LOGIN_FAIL_WINDOW: int = Field(default=900)  # 15 minutes
    EMAIL_LOCK_TTL: int = Field(default=900)  # 15 minutes
    LOGIN_FAIL_IP_THRESHOLD: int = Field(default=30)
    IP_LOCK_TTL: int = Field(default=900)  # 15 minutes
    IP_LOCK_ESCALATION: bool = Field(default=True)
    IP_LOCK_MAX_TTL: int = Field(default=86400)  # 24 hours

    @model_validator(mode="before")
    @classmethod
    def parse_cors_origins(cls, data):
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(data, dict) and "CORS_ORIGINS" in data:
            cors_origins = data["CORS_ORIGINS"]
            if isinstance(cors_origins, str):
                data["CORS_ORIGINS"] = [
                    origin.strip() for origin in cors_origins.split(",") if origin.strip()
                ]
            elif isinstance(cors_origins, list):
                data["CORS_ORIGINS"] = cors_origins
        return data

    def __init__(self, **kwargs):
        """Validate settings on initialization."""
        # Normalize CORS_ORIGINS to list if it's a string
        if "CORS_ORIGINS" in kwargs and isinstance(kwargs["CORS_ORIGINS"], str):
            kwargs["CORS_ORIGINS"] = [
                origin.strip() for origin in kwargs["CORS_ORIGINS"].split(",") if origin.strip()
            ]
        super().__init__(**kwargs)
        # Ensure CORS_ORIGINS is a list after initialization
        if isinstance(self.CORS_ORIGINS, str):
            object.__setattr__(
                self,
                "CORS_ORIGINS",
                [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()],
            )
        # Fail fast in production if critical vars are missing
        if self.ENV == "prod":
            if not self.DATABASE_URL or self.DATABASE_URL.startswith(
                "postgresql+psycopg2://exam_user:change_me"
            ):
                raise ValueError("DATABASE_URL must be set in production")
            if not self.JWT_SECRET or self.JWT_SECRET == "change_me_super_secret":
                raise ValueError("JWT_SECRET must be set in production")
            if not self.TOKEN_PEPPER:
                raise ValueError("TOKEN_PEPPER must be set in production")
            # In prod, Redis should be required for security controls
            if self.REDIS_ENABLED and not self.REDIS_URL:
                raise ValueError("REDIS_URL must be set in production when REDIS_ENABLED=true")
            if self.REDIS_ENABLED:
                self.REDIS_REQUIRED = True
            if not self.MFA_ENCRYPTION_KEY:
                raise ValueError("MFA_ENCRYPTION_KEY must be set in production")


# Global settings instance
settings = Settings()
