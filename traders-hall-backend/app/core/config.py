from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings) :
    model_config = SettingsConfigDict(env_file = '.env', extra="ignore")
    PROJECT_NAME: str = "Traders Hall"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me"

    POSTGRES_USER: str = "traders"
    POSTGRES_PASSWORD: str = "traders"
    POSTGRES_DB: str = "traders_hall"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
@lru_cache
def get_settings() -> Settings:
    return Settings()