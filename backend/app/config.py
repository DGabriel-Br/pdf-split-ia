from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_text_model: str = "llama3.1"
    ollama_vision_model: str = ""
    ocr_text_threshold: int = 50
    ocr_confidence_threshold: float = 0.4
    tesseract_cmd: str = ""  # empty = use system PATH; on Windows set full path in .env
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    max_upload_size_mb: int = 50
    storage_upload_dir: str = "storage/uploads"
    storage_output_dir: str = "storage/outputs"
    job_ttl_seconds: int = 3600
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
