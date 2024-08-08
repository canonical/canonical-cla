from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILES = (".env", ".env.local")


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_prefix="db_",
    )

    host: str
    port: int
    user: str
    password: SecretStr
    database: str

    @staticmethod
    def dsn():
        self = DatabaseConfig()  # type: ignore
        return f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"
