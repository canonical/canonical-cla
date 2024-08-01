
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
    database: str = "canonical_cla"
