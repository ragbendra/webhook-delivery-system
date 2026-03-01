from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    DB_HOST: str = Field(default="db")
    DB_PORT: int = Field(default=3306)
    DB_USER: str = Field(default="webhook_user")
    DB_PASSWORD: str = Field(default="")
    DB_NAME: str = Field(default="webhook_db")

    # JWT
    JWT_SECRET: str = Field(..., min_length=1)
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(..., gt=0)

    # App
    APP_ENV: str = Field(default="development")
    APP_DEBUG: bool = Field(default=False)

    # Worker
    WORKER_POLL_INTERVAL_SECONDS: float = Field(default=2.0, gt=0)
    WORKER_MAX_DELIVERY_ATTEMPTS: int = Field(default=5, ge=1)
    WORKER_MIN_BACKOFF_SECONDS: float = Field(default=1.0, ge=0)
    WORKER_MAX_BACKOFF_SECONDS: float = Field(default=60.0, ge=0)
    WORKER_HTTP_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0)
    WORKER_SUCCESS_STATUS_CODES: str = Field(default="200,201,202,204")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def WORKER_SUCCESS_STATUS_CODE_LIST(self) -> list[int]:
        codes: list[int] = []
        for raw in self.WORKER_SUCCESS_STATUS_CODES.split(","):
            value = raw.strip()
            if not value:
                continue
            codes.append(int(value))
        return codes or [200, 201, 202, 204]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
