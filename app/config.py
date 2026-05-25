from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    KEYCLOAK_SERVER_URL: str
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_CLIENT_SECRET: str
    #GEMINI_API_KEY: str = "" добавить API KEY 

    SECRET_KEY: str
    APP_NAME: str
    DEBUG: bool = False

    # YandexGPT
    YANDEX_API_KEY: str
    YANDEX_FOLDER_ID: str
    YANDEX_MODEL: str = "yandexgpt-lite"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()