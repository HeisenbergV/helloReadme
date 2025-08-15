"""
项目配置文件
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """项目配置类"""
    
    # 项目基础配置
    PROJECT_NAME: str = "helloReadme"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # GitHub API配置
    GITHUB_TOKEN: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    GITHUB_SEARCH_QUERY: str = "AI machine learning artificial intelligence"
    GITHUB_MAX_REPOS: int = 1000
    GITHUB_RATE_LIMIT_DELAY: float = 1.0  # 请求间隔(秒)
    
    # 数据库配置
    DATABASE_URL: str = Field(
        default="sqlite:///./hello_readme.db",
        env="DATABASE_URL"
    )
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # 向量数据库配置
    VECTOR_DB_PATH: str = "./vector_db"
    VECTOR_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = "./logs/hello_readme.log"
    
    # 采集配置
    COLLECTION_BATCH_SIZE: int = 50
    COLLECTION_INTERVAL_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局配置实例
settings = Settings()

# 确保日志目录存在
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
