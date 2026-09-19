from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@db:5432/document_pipeline"
    REDIS_BROKER_URL: str = "redis://redis:6379/0"
    REDIS_BACKEND_URL: str = "redis://redis:6379/1"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
