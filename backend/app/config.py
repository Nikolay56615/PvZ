from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_secret: str = "change_me"
    app_jwt_expires_min: int = 60
    app_env: str = "dev"
    app_tenant: str = "fake"

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "pvz"
    db_password: str = "change_me"
    db_name: str = "pvzdb"

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()