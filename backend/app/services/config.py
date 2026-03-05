from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_secret: str = "change_me"
    app_jwt_expires_min: int = 60
    app_env: str = "dev"
    app_tenant: str = "fake"

    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "pvz"
    db_password: str = "change_me"
    db_name: str = "pvzdb"

    dynsec_enabled: bool = True
    dynsec_control_topic: str = "$CONTROL/dynamic-security/v1"
    dynsec_response_topic: str = "$CONTROL/dynamic-security/v1/response"
    dynsec_admin_username: str | None = None
    dynsec_admin_password: str | None = None
    
    allow_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    # @field_validator('allow_origin', mode='before')
    # @classmethod
    # def split_string_into_list(cls, v: Any) -> Any:
    #     if isinstance(v, str):
    #         return [item.strip() for item in v.split(',')]
    #     return v

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()
