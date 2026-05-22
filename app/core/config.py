from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Redis (optional — used for cross-instance rate limiting)
    redis_url: str = ""
    ratelimit_prefix: str = ""

    # App
    environment: Literal["development", "staging", "production"] = "development"
    allowed_origins: str = "http://localhost:3000"
    auth_callback_url: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        if self.environment in ("staging", "production"):
            missing = [
                name
                for name, val in [
                    ("SUPABASE_SERVICE_ROLE_KEY", self.supabase_service_role_key),
                    ("SUPABASE_URL", self.supabase_url),
                ]
                if not val
            ]
            if missing:
                raise ValueError(
                    f"Missing required {self.environment} environment variables: "
                    f"{', '.join(missing)}"
                )
        return self

    def get_auth_callback_url(self) -> str:
        if self.auth_callback_url:
            return self.auth_callback_url
        if self.environment == "staging":
            return "https://staging.domelayer.com/auth/callback"
        if self.environment == "production":
            return "https://domelayer.com/auth/callback"
        return "http://localhost:3000/auth/callback"


settings = Settings()
