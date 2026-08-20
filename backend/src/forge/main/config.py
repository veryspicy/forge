from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/forge"

    # Redis
    redis_url: str = "redis://:redispass@localhost:6380/0"

    # App
    secret_key: str = "dev-secret-key-change-in-production"
    debug: bool = True
    region: str = "na"
    default_currency: str = "USD"

    # OpenAI
    openai_api_key: str = "sk-placeholder"

    # AI Service
    ai_service_url: str = "http://localhost:8001"

    # MinIO
    minio_endpoint: str = "localhost:9002"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "product-images"
    # 显式指定 MinIO 协议（true=HTTPS），不依赖主机名猜测；容器内服务名走 HTTP
    minio_secure: bool = False

    # JWT
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
