from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Crawler Configuration loaded from Environment Variables.
    """
    CRAWLER_ID: str = "crawler-001"
    CRAWLER_NAME: str = "simple-crawler"
    SOURCE_URL: str = "https://jsonplaceholder.typicode.com/posts"
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "aiops_demo"
    MONGODB_COLLECTION: str = "crawler_results"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "demo"
    LOG_FILE_PATH: str = "logs/crawler.log"
    SIMULATED_ERROR: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
