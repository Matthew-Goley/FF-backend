from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/freshforward"

    # Auth / JWT
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # CORS - comma-separated list of allowed origins
    frontend_url: str = "http://localhost:5173"


settings = Settings()
