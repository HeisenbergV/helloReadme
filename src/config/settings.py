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
    
    # AI服务配置
    # DeepSeek配置
    DEEPSEEK_API_KEY: str = "sk-9f058b9120d84939a0e08e9f6a3b811b"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    # OpenAI配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com"
    
    # Anthropic Claude配置
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    
    # 百度文心一言配置
    BAIDU_API_KEY: str = ""
    BAIDU_SECRET_KEY: str = ""
    BAIDU_BASE_URL: str = "https://aip.baidubce.com"
    
    # 阿里通义千问配置
    ALIBABA_API_KEY: str = ""
    ALIBABA_BASE_URL: str = "https://dashscope.aliyuncs.com"
    
    # 智谱AI配置
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn"
    
    # Ollama配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # AI默认配置
    DEFAULT_LLM_MODEL: str = "deepseek-chat"
    DEFAULT_LLM_TEMPERATURE: float = 0.7
    DEFAULT_LLM_MAX_TOKENS: int = 1000
    
    # AI服务优先级 (本地服务优先)
    
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
