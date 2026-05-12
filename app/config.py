from functools import lru_cache

from sqlalchemy.engine import URL
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://test:test@localhost:5432/hello_copilot"
    database_driver: str = "postgresql+psycopg"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "hello_copilot"
    database_user: str = "test"
    database_password: str = "test"
    external_source_api_url: str = ""
    external_source_system: str = "external_api"
    auth_enabled: bool = False
    auth_issuer: str = ""
    auth_audience: str = ""
    auth_jwks_url: str = ""
    auth_algorithms: str = "RS256"
    auth_required_groups: str = ""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def sqlalchemy_database_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        return URL.create(
            drivername=self.database_driver,
            username=self.database_user,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
