"""Application core configuration module."""

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_ENVIRONMENTS = frozenset({"development"})
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


class Settings(BaseSettings):
    """Application settings with environment variable support.

    Security-relevant defaults fail closed: the environment defaults to ``production``,
    anonymous access is disabled, and CORS only allows local frontend origins.
    """

    PROJECT_NAME: str = "Agent Evaluation Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    DATABASE_URL: str = "sqlite:///./agent_eval.db"
    BUILD_DATE: str = "2026-11-08T12:00:00Z"
    COMMIT_SHA: str = "unknown"

    # Anonymous access: honoured ONLY when ENVIRONMENT=development. Anonymous callers
    # receive the read-only VIEWER role and can never perform mutations.
    ALLOW_ANONYMOUS_VIEWER: bool = False

    # Comma-separated list of browser origins allowed by CORS. Wildcards are rejected.
    # Unset: local frontend origins in development/test, a startup error in other environments.
    CORS_ALLOWED_ORIGINS: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def _normalize_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"development", "test", "staging", "production"}:
            raise ValueError(
                "ENVIRONMENT must be one of: development, test, staging, production"
            )
        return normalized

    @model_validator(mode="after")
    def _validate_cors(self) -> "Settings":
        if self.CORS_ALLOWED_ORIGINS is None:
            if self.ENVIRONMENT not in DEVELOPMENT_ENVIRONMENTS | {"test"}:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must be set to an explicit origin list outside "
                    "development and test environments."
                )
        elif "*" in self.CORS_ALLOWED_ORIGINS:
            raise ValueError("CORS_ALLOWED_ORIGINS must not contain a wildcard '*'.")
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Parsed, de-duplicated CORS origin allowlist."""
        raw_value = self.CORS_ALLOWED_ORIGINS
        if raw_value is None:
            raw_value = DEFAULT_CORS_ORIGINS
        seen: list[str] = []
        for raw in raw_value.split(","):
            origin = raw.strip().rstrip("/")
            if origin and origin not in seen:
                seen.append(origin)
        return seen

    @property
    def anonymous_access_enabled(self) -> bool:
        """True only in development with ALLOW_ANONYMOUS_VIEWER explicitly enabled."""
        return self.ENVIRONMENT in DEVELOPMENT_ENVIRONMENTS and self.ALLOW_ANONYMOUS_VIEWER


settings = Settings()
