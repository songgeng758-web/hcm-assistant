"""
全局配置
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 项目基础路径
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # 数据目录
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    OUTPUT_DIR: Path = DATA_DIR / "outputs"
    TEMPLATE_DIR: Path = DATA_DIR / "templates"

    # CORS 允许的来源（前端开发地址）
    CORS_ORIGINS: list = [
        "http://localhost:5173",  # Vite 默认端口
        "http://localhost:3000",
    ]

    # 文件大小限制（单位：字节）50MB
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024

    class Config:
        env_file = ".env"


settings = Settings()

# 确保数据目录存在
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
