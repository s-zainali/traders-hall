from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file = '.env', extra="ignore")
    PROJECT_NAME: str = "Traders Hall"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me"

    DATABASE_URL: Optional[str] = None

    POSTGRES_USER: str = "traders"
    POSTGRES_PASSWORD: str = "traders"
    POSTGRES_DB: str = "traders_hall"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "?" in url:
                base_url, query = url.split("?", 1)
                params = [p for p in query.split("&") if not p.startswith("sslmode=")]
                url = base_url + ("?" + "&".join(params) if params else "")
                
            return url

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
@lru_cache
def get_settings() -> Settings:
    return Settings()