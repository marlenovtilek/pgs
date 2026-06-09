from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PGS (Parking Guidance Service)"
    debug: bool = True
    database_url: str = "postgresql+psycopg2://pgs:pgs@localhost:5432/pgs"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_client_id: str = "pgs-mqtt-listener"
    mqtt_keepalive: int = 60
    auth_secret_key: str = "pgs-dev-auth-secret-change-me"
    auth_cookie_name: str = "pgs_auth"
    auth_cookie_max_age: int = 60 * 60 * 24 * 7
    auth_cookie_secure: bool = False
    auth_registration_enabled: bool = False
    api_token: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None
    led_adapter: str = "mock"
    led_http_path: str = "/api/v1/led/commands"
    led_http_timeout: float = 3.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
