from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    AIOps Controller Configuration loaded from Environment Variables.
    """
    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"
    ELASTICSEARCH_CRAWLER_INDEX: str = "scrm-aiops-crawler-*"
    ELASTICSEARCH_CONTROLLER_INDEX: str = "scrm-aiops-controller"
    MONGODB_URI: str = "mongodb://localhost:27017"
    
    NVIDIA_API_KEY: str = "demo_key"
    NVIDIA_MODEL: str = "meta/llama-3.1-405b-instruct"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    AI_CONFIDENCE_THRESHOLD: float = 0.80
    
    AIOPS_DEMO_MODE: bool = True
    POLL_INTERVAL_SECONDS: int = 5
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
