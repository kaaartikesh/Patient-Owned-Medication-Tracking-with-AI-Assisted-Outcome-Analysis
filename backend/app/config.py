from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        placeholder_values = {
            "change-this-to-something-random-and-long-later",
            "changeme",
            "secret",
            "placeholder",
            "your-secret-key",
            "your-secret-key-here",
            "your-32-character-or-longer-secret-key-here-12345",
        }
        val = v.strip()
        if len(val) < 32:
            raise ValueError("JWT_SECRET is shorter than 32 characters. Refusing to start.")
        if val in placeholder_values or "change-this" in val.lower() or "placeholder" in val.lower():
            raise ValueError("JWT_SECRET cannot be a placeholder value. Refusing to start.")
        return val

settings = Settings()