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


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        extra="ignore",
    )

    secret_key: SecretStr

    database: DatabaseConfig = DatabaseConfig()  # type: ignore
    redis: RedisConfig = RedisConfig()  # type: ignore


config = Config()  # type: ignore
