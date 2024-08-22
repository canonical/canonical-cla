from email.utils import formataddr

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILES = (".env", ".env.local")


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
    from_email: str = formataddr(("Canonical CLA", "cla@canonical.com"))
    legal_contact_email: str = "legal@canonical.com"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        extra="ignore",
    )

    secret_key: SecretStr
    app_name: str = "Canonical CLA (dev)"
    debug_mode: bool = False

    github_oauth: GitHubOAuthConfig = GitHubOAuthConfig()  # type: ignore
    launchpad_oauth: LaunchpadOAuthConfig = LaunchpadOAuthConfig()  # type: ignore
    database: DatabaseConfig = DatabaseConfig()  # type: ignore
    redis: RedisConfig = RedisConfig()  # type: ignore
    smtp: SMTPConfig = SMTPConfig()  # type: ignore


config = Config()  # type: ignore
