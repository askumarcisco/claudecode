from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Video Creator"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OUTPUT_DIR: str = "./outputs"
    UPLOAD_DIR: str = "./uploads"
    WHISPER_MODEL: str = "base"
    FRONTEND_URL: str = "http://localhost:3000"
    # localhost:5173 is the Vite dev server (docker-compose.dev.yml); :80 is
    # the nginx-served production build (docker-compose.yml).
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:80",
        "http://localhost",
    ]

    class Config:
        env_file = ".env"


settings = Settings()
