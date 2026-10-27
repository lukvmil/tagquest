from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    session_secret: SecretStr
    rc_client_id: str
    rc_client_secret: SecretStr
    host: str = "localhost:8000"
    print_mode: str = "remote"
    local_print_url: str | None = None
    
settings = Settings()