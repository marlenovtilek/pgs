from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PGS (Parking Guidance Service)"
    debug: bool = True
    database_url: str = "postgresql+psycopg2://pgs:pgs@localhost:5432/pgs"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
