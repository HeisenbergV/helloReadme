"""
统一日志配置模块
"""
import os
import sys
from pathlib import Path
from loguru import logger

# 确保日志目录存在
log_dir = Path(__file__).parent.parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)

# 移除默认的日志处理器
logger.remove()

# 添加控制台日志处理器
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    level="INFO"
)

# 添加文件日志处理器（按日期）
logger.add(
    log_dir / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    encoding="utf-8"
)

# 添加错误日志处理器
logger.add(
    log_dir / "error_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="ERROR",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    encoding="utf-8"
)

def get_logger(name: str = None):
    """获取日志记录器"""
    if name:
        return logger.bind(name=name)
    return logger
