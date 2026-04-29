from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "HospitalCallbackSystem"
    log_level: str = "INFO"

    # Database (本地开发默认使用 SQLite，生产环境切换为 PostgreSQL)
    database_url: str = "sqlite+aiosqlite:///./callback.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Claude API
    anthropic_api_key: str = ""
    # 使用 Claude 最新模型
    claude_model: str = "claude-sonnet-4-20250514"

    # Voice service (optional placeholders)
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
