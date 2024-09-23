import logging
from email.utils import formataddr

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILES = (".env", ".env.local")

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="db_",
        extra="ignore",
    )

    host: str
    port: int
    username: str
    password: SecretStr
    database: str

    def dsn(self):
        return f"postgresql+asyncpg://{self.username}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"


class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="redis_",
        extra="ignore",
    )

    host: str
    port: int

    def dsn(self):
        return f"redis://{self.host}:{self.port}"


class GitHubOAuthConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="github_oauth_",
        extra="ignore",
    )

    client_id: str
    client_secret: SecretStr
    scope: str = "user:email"


class LaunchpadOAuthConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="launchpad_oauth_",
        extra="ignore",
    )

    scope: str = "READ_PRIVATE"


class SMTPConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="smtp_",
        extra="ignore",
    )

    host: str
    port: int
    username: str
    password: SecretStr
    from_email: str = formataddr(("Canonical CLA", "noreply+cla@canonical.com"))
    legal_contact_email: str = formataddr(
        ("Canonical's Legal Team", "legal@canonical.com")
    )


class RateLimitConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="rate_limit_",
        extra="ignore",
    )

    limit: int = 100
    period: int = 60
    whitelist: list[str] = []


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        extra="ignore",
    )

    secret_key: SecretStr
    app_url: str
    app_name: str = "Canonical CLA (dev)"
    debug_mode: bool = False
    environment: str = "development"

    github_oauth: GitHubOAuthConfig = GitHubOAuthConfig()  # type: ignore
    launchpad_oauth: LaunchpadOAuthConfig = LaunchpadOAuthConfig()  # type: ignore
    database: DatabaseConfig = DatabaseConfig()  # type: ignore
    redis: RedisConfig = RedisConfig()  # type: ignore
    smtp: SMTPConfig = SMTPConfig()  # type: ignore

    rate_limit: RateLimitConfig = RateLimitConfig()  # type: ignore
    sentry_dsn: str | None = None


config = Config()  # type: ignore
