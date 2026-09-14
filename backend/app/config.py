# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "旅游记忆系统")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8003"))

    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
    DB_NAME = os.getenv("DB_NAME", "trip_memory")

    SECRET_KEY = os.getenv("SECRET_KEY", "trip-memory-secret-key-2024")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

    # TripCanvas对接
    TRIPCANVAS_API_URL = os.getenv("TRIPCANVAS_API_URL", "http://127.0.0.1:8002/api")
    TRIPCANVAS_API_TOKEN = os.getenv("TRIPCANVAS_API_TOKEN", "")
    TRIPCANVAS_SERVICE_USERNAME = os.getenv("TRIPCANVAS_SERVICE_USERNAME", "")
    TRIPCANVAS_SERVICE_PASSWORD = os.getenv("TRIPCANVAS_SERVICE_PASSWORD", "")

    # AI大模型
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"


settings = Settings()
