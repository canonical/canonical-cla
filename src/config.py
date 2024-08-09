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

    @staticmethod
    def dsn():
        self = DatabaseConfig()  # type: ignore
        return f"postgresql+asyncpg://{self.username}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"


class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="redis_",
        extra="ignore",
    )

    host: str
    port: int

    @staticmethod
    def dsn():
        self = RedisConfig()  # type: ignore
        return f"redis://{self.host}:{self.port}"
