"""Application settings and configuration."""

from typing import Literal

from pydantic import Field, model_validator  # type: ignore
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

    # CORS Configuration - Deny-by-default with env allowlists
    CORS_ALLOW_ORIGINS_PUBLIC: str = Field(
        default="",
        description="Comma-separated exact origins for public endpoints (no wildcards)",
    )
    CORS_ALLOW_ORIGINS_APP: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        description="Comma-separated exact origins for app endpoints (no wildcards)",
    )
    CORS_ALLOW_METHODS: str = Field(
        default="GET,POST,PUT,PATCH,DELETE,OPTIONS",
        description="Comma-separated allowed HTTP methods",
    )
    CORS_ALLOW_HEADERS: str = Field(
        default="Authorization,Content-Type,X-Request-ID",
        description="Comma-separated allowed request headers",
    )
    CORS_EXPOSE_HEADERS: str = Field(
        default="X-Request-ID,X-Response-Time-ms,X-DB-Queries,X-DB-Time-ms",
        description="Comma-separated headers to expose to client",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=False,
        description="Allow credentials in CORS requests (set true if using cookie auth)",
    )
    # Legacy CORS_ORIGINS for backward compatibility (will be merged with CORS_ALLOW_ORIGINS_APP)
    CORS_ORIGINS: str | list[str] = Field(default="http://localhost:3000,http://localhost:3001")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    # Security - JWT
    JWT_SECRET: str | None = Field(default=None, description="Legacy: single JWT signing key (use JWT_SIGNING_KEY_CURRENT instead)")
    JWT_SIGNING_KEY_CURRENT: str | None = Field(
        default=None, description="Current JWT signing key (preferred over JWT_SECRET)"
    )
    JWT_SIGNING_KEY_PREVIOUS: str | None = Field(
        default=None, description="Previous JWT signing key for zero-downtime rotation"
    )
    JWT_ALG: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14)
    TOKEN_PEPPER: str | None = Field(default=None)  # Server-side pepper for token hashing (legacy)
    AUTH_TOKEN_PEPPER: str | None = Field(
        default=None, description="Server-side pepper for auth token hashing (preferred over TOKEN_PEPPER)"
    )
    AUTH_TOKEN_PEPPER_CURRENT: str | None = Field(
        default=None, description="Current pepper for auth token hashing (preferred over AUTH_TOKEN_PEPPER)"
    )
    AUTH_TOKEN_PEPPER_PREVIOUS: str | None = Field(
        default=None, description="Previous pepper for auth token hashing (for zero-downtime rotation)"
    )

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

    # Email configuration
    EMAIL_PROVIDER: str = Field(default="console", description="Email provider: console|smtp")
    SMTP_HOST: str | None = Field(default=None, description="SMTP server host")
    SMTP_PORT: int | None = Field(default=None, description="SMTP server port")
    SMTP_FROM_EMAIL: str | None = Field(default=None, description="SMTP from email address")
    SMTP_FROM_NAME: str | None = Field(default=None, description="SMTP from name")
    SMTP_USE_TLS: bool = Field(default=False, description="Use TLS for SMTP")
    SMTP_USE_SSL: bool = Field(default=False, description="Use SSL for SMTP")
    SMTP_USER: str | None = Field(default=None, description="SMTP username (if auth required)")
    SMTP_PASS: str | None = Field(default=None, description="SMTP password (if auth required)")

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
    
    # System flags cache TTL
    SYSTEM_FLAGS_CACHE_TTL_SECONDS: int = Field(
        default=10,
        description="Cache TTL in seconds for system flags (e.g., EXAM_MODE). Default 10s."
    )
    
    # Exam-Time Mode (legacy env var - now uses DB-backed system_flags table)
    # This is kept for backward compatibility but system_flags.EXAM_MODE is source of truth
    EXAM_MODE: bool = Field(
        default=False,
        description="Legacy env var - use system_flags.EXAM_MODE instead. When enabled, disables heavy analytics recompute, admin bulk jobs, and defers background recalculations"
    )

    # IRT (Item Response Theory) - Shadow/offline only
    FEATURE_IRT_SHADOW: bool = Field(
        default=True,
        description="Allow offline IRT calibration + admin visibility. Default True.",
    )
    FEATURE_IRT_ACTIVE: bool = Field(
        default=False,
        description="When True, IRT may be used for student-facing decisions. Default False.",
    )
    FEATURE_IRT_MODEL: Literal["IRT_2PL", "IRT_3PL"] = Field(
        default="IRT_2PL",
        description="IRT model type to use when active. Default IRT_2PL.",
    )
    FEATURE_IRT_SCOPE: Literal["none", "shadow_only", "selection_only", "scoring_only", "selection_and_scoring"] = Field(
        default="none",
        description="IRT activation scope. Ignored unless FEATURE_IRT_ACTIVE=true. Default none.",
    )

    # Neo4j Configuration
    NEO4J_ENABLED: bool = Field(
        default=False,
        description="Enable Neo4j for concept graph. If False, graph operations degrade gracefully.",
    )
    NEO4J_URI: str = Field(
        default="bolt://neo4j:7687",
        description="Neo4j Bolt connection URI",
    )
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="change_me", description="Neo4j password")
    NEO4J_DATABASE: str = Field(
        default="neo4j",
        description="Neo4j database name (leave blank for default)",
    )
    NEO4J_MAX_CONNECTION_LIFETIME: int = Field(
        default=3600,
        description="Max connection lifetime in seconds (default 1 hour)",
    )

    # Elasticsearch Configuration
    ELASTICSEARCH_ENABLED: bool = Field(
        default=False,
        description="Enable Elasticsearch for search functionality. If False, search degrades gracefully.",
    )
    ELASTICSEARCH_URL: str = Field(
        default="http://elasticsearch:9200",
        description="Elasticsearch HTTP URL",
    )
    ELASTICSEARCH_USERNAME: str | None = Field(
        default=None,
        description="Elasticsearch username (optional, for secured clusters)",
    )
    ELASTICSEARCH_PASSWORD: str | None = Field(
        default=None,
        description="Elasticsearch password (optional, for secured clusters)",
    )
    ELASTICSEARCH_INDEX_PREFIX: str = Field(
        default="platform",
        description="Prefix for all Elasticsearch indices",
    )
    ELASTICSEARCH_MIN_PUBLISHED_QUESTIONS: int = Field(
        default=500,
        description="Minimum number of published questions required for ES readiness (default 500)",
    )
    ELASTICSEARCH_SYNC_FRESHNESS_HOURS: int = Field(
        default=24,
        description="Maximum hours since last successful sync for ES readiness (default 24)",
    )
    ELASTICSEARCH_ERROR_BUDGET_RUNS: int = Field(
        default=3,
        description="Number of recent runs to check for failures in error budget (default 3)",
    )

    # ============================================
    # Neo4j Graph Readiness Configuration
    # ============================================
    MIN_GRAPH_NODES: int = Field(
        default=200,
        description="Minimum number of Concept nodes required for graph readiness (default 200)",
    )
    MIN_GRAPH_EDGES: int = Field(
        default=100,
        description="Minimum number of PREREQ edges required for graph readiness (default 100)",
    )
    GRAPH_SYNC_FRESHNESS_HOURS: int = Field(
        default=24,
        description="Maximum hours since last successful sync for graph readiness (default 24)",
    )
    GRAPH_ERROR_BUDGET_RUNS: int = Field(
        default=3,
        description="Number of recent runs to check for failures in error budget (default 3)",
    )
    FEATURE_GRAPH_ACTIVE: bool = Field(
        default=False,
        description="Feature flag to allow 'active' mode (default False, shadow-only for now)",
    )
    FEATURE_STUDENT_CONCEPT_EXPLORER: bool = Field(
        default=False,
        description="Feature flag to enable student concept exploration (default False)",
    )
    ELASTICSEARCH_REQUEST_TIMEOUT_MS: int = Field(
        default=2000,
        description="Request timeout in milliseconds",
    )
    ELASTICSEARCH_BULK_BATCH_SIZE: int = Field(
        default=500,
        description="Bulk operation batch size",
    )
    ELASTICSEARCH_RETRY_MAX: int = Field(
        default=5,
        description="Maximum number of retries for failed requests",
    )

    # ============================================
    # Snowflake Warehouse Configuration
    # ============================================
    SNOWFLAKE_ENABLED: bool = Field(
        default=False,
        description="Enable Snowflake warehouse integration. Default False (hard-disabled).",
    )
    SNOWFLAKE_ACCOUNT: str | None = Field(
        default=None,
        description="Snowflake account identifier (e.g., 'xy12345.us-east-1')",
    )
    SNOWFLAKE_USER: str | None = Field(
        default=None,
        description="Snowflake username",
    )
    SNOWFLAKE_PASSWORD: str | None = Field(
        default=None,
        description="Snowflake password",
    )
    SNOWFLAKE_WAREHOUSE: str | None = Field(
        default=None,
        description="Snowflake warehouse name",
    )
    SNOWFLAKE_DATABASE: str | None = Field(
        default=None,
        description="Snowflake database name",
    )
    SNOWFLAKE_SCHEMA: str = Field(
        default="RAW",
        description="Snowflake schema name (default: RAW)",
    )
    FEATURE_ALLOW_SNOWFLAKE_CONNECT: bool = Field(
        default=False,
        description="Feature flag to allow actual Snowflake connections. Default False (no connections by default).",
    )
    FEATURE_TRANSFORMS_OPTIONAL: bool = Field(
        default=False,
        description="If True, transform readiness is optional for warehouse activation. Default False (transforms required).",
    )
    WAREHOUSE_PIPELINE_FRESHNESS_HOURS: int = Field(
        default=24,
        description="Maximum hours since last successful export/transform run for readiness (default 24)",
    )
    WAREHOUSE_ERROR_BUDGET_RUNS: int = Field(
        default=3,
        description="Number of recent runs to check for failures in error budget (default 3)",
    )

    # Mock ranking (Task 145): Python baseline + Go shadow/active
    GO_RANKING_ENABLED: bool = Field(
        default=False,
        description="Enable Go ranking service. Required for go_shadow/go_active. Default False.",
    )
    RANKING_GO_URL: str = Field(
        default="http://ranking-go:8080",
        description="Base URL of Go ranking service (default ranking-go:8080)",
    )
    RANKING_PARITY_EPSILON: float = Field(
        default=0.001,
        description="Max allowed abs percentile diff for parity (default 0.001)",
    )
    RANKING_PARITY_K: int = Field(
        default=10,
        description="Number of recent shadow runs to check parity (default 10)",
    )
    RANKING_ERROR_BUDGET_RUNS: int = Field(
        default=3,
        description="No failures in last N runs for go_active readiness (default 3)",
    )

    # Brute-force Protection
    LOGIN_FAIL_EMAIL_THRESHOLD: int = Field(default=8)
    LOGIN_FAIL_WINDOW: int = Field(default=900)  # 15 minutes
    EMAIL_LOCK_TTL: int = Field(default=900)  # 15 minutes
    LOGIN_FAIL_IP_THRESHOLD: int = Field(default=30)
    IP_LOCK_TTL: int = Field(default=900)  # 15 minutes
    IP_LOCK_ESCALATION: bool = Field(default=True)
    IP_LOCK_MAX_TTL: int = Field(default=86400)  # 24 hours

    # Security Headers Configuration
    ENABLE_HSTS: bool = Field(
        default=False,
        description="Enable HSTS header (only if ENV=prod and HTTPS guaranteed at edge)",
    )
    ENABLE_CSP: bool = Field(
        default=False,
        description="Enable Content-Security-Policy header (default false, can break embeds)",
    )

    # Request body size limits (input hardening)
    MAX_BODY_BYTES_DEFAULT: int = Field(
        default=2_000_000,
        description="Max request body size in bytes for general API (default 2MB). Enforced by middleware.",
    )
    MAX_BODY_BYTES_IMPORT: int = Field(
        default=10_000_000,
        description="Max request body size for admin import endpoint (default 10MB). Override for /v1/admin/import/questions.",
    )
    IMPORT_MAX_ROWS: int = Field(
        default=5000,
        description="Max rows per bulk import (CSV). Rejects with VALIDATION_LIMIT_EXCEEDED if exceeded.",
    )

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
            # Require JWT signing key (CURRENT preferred, fallback to JWT_SECRET for backward compatibility)
            jwt_key = self.JWT_SIGNING_KEY_CURRENT or self.JWT_SECRET
            if not jwt_key or jwt_key == "change_me_super_secret":
                raise ValueError("JWT_SIGNING_KEY_CURRENT or JWT_SECRET must be set in production")
            # Require AUTH_TOKEN_PEPPER_CURRENT, AUTH_TOKEN_PEPPER, or TOKEN_PEPPER in production
            pepper = self.AUTH_TOKEN_PEPPER_CURRENT or self.AUTH_TOKEN_PEPPER or self.TOKEN_PEPPER
            if not pepper:
                raise ValueError("AUTH_TOKEN_PEPPER_CURRENT, AUTH_TOKEN_PEPPER, or TOKEN_PEPPER must be set in production")
            # In prod, Redis should be required for security controls
            if self.REDIS_ENABLED and not self.REDIS_URL:
                raise ValueError("REDIS_URL must be set in production when REDIS_ENABLED=true")
            if self.REDIS_ENABLED:
                self.REDIS_REQUIRED = True
            if not self.MFA_ENCRYPTION_KEY:
                raise ValueError("MFA_ENCRYPTION_KEY must be set in production")

    def _parse_comma_separated(self, value: str) -> list[str]:
        """Parse comma-separated string into list, trimming spaces and ignoring empties."""
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_allow_origins_list(self) -> list[str]:
        """Get combined list of allowed CORS origins (public + app + legacy)."""
        origins: set[str] = set()
        # Add public origins
        origins.update(self._parse_comma_separated(self.CORS_ALLOW_ORIGINS_PUBLIC))
        # Add app origins
        origins.update(self._parse_comma_separated(self.CORS_ALLOW_ORIGINS_APP))
        # Add legacy CORS_ORIGINS for backward compatibility
        if isinstance(self.CORS_ORIGINS, str):
            origins.update(self._parse_comma_separated(self.CORS_ORIGINS))
        elif isinstance(self.CORS_ORIGINS, list):
            origins.update(self.CORS_ORIGINS)
        return sorted(list(origins))

    @property
    def cors_allow_methods_list(self) -> list[str]:
        """Get list of allowed CORS methods."""
        return self._parse_comma_separated(self.CORS_ALLOW_METHODS)

    @property
    def cors_allow_headers_list(self) -> list[str]:
        """Get list of allowed CORS headers."""
        return self._parse_comma_separated(self.CORS_ALLOW_HEADERS)

    @property
    def cors_expose_headers_list(self) -> list[str]:
        """Get list of exposed CORS headers."""
        return self._parse_comma_separated(self.CORS_EXPOSE_HEADERS)


# Global settings instance
settings = Settings()
