"""
系統設定檔
從環境變數讀取所有設定值。
必填欄位（SECRET_KEY / POSTGRES_PASSWORD）未設定時，啟動直接報錯，避免使用危險預設值。
"""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 環境
    ENV: str = "development"            # development | production

    # 資料庫
    POSTGRES_USER: str = "babycorn"
    POSTGRES_PASSWORD: str              # 無預設值，必須在 .env 設定
    POSTGRES_DB: str = "babycorn_erp"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # JWT 設定（必填，無預設值）
    SECRET_KEY: str                     # 無預設值，必須在 .env 設定
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS（多個來源用逗號分隔）
    CORS_ORIGINS: str = "http://localhost:3000"

    # 上傳設定
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 20

    # 備份設定
    BACKUP_KEEP_DAYS: int = 7

    # 敏感欄位加密（Fernet，44 字元 base64url；留空則不加密）
    # 產生方式：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # Email 設定（SMTP，選填）
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "玉米筍ERP系統"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY 長度必須至少 32 字元，請在 .env 設定強密鑰")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """將逗號分隔的 CORS_ORIGINS 字串轉為清單"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"


# 全域設定實例（啟動時即驗證，缺少必填欄位會立即報錯）
settings = Settings()
