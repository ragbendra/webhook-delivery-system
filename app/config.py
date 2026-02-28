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

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
