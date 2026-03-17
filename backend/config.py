"""
系統設定檔
從環境變數讀取所有設定值
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 資料庫
    POSTGRES_USER: str = "babycorn"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "babycorn_erp"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # JWT 設定
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 上傳設定
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 20

    # Email 設定（SMTP）
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "玉米筍ERP系統"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"


# 全域設定實例
settings = Settings()
