"""
LLM服务模块 - AI调用相关
包含大语言模型调用、多种AI后端支持等功能
"""

from .base import AIServiceInterface, AIRequest, AIResponse, AIModelType
from .manager import AIServiceManager
from .deepseek_api import DeepSeekAPIService
from .ollama_service import OllamaService

__all__ = [
    'AIServiceInterface', 
    'AIRequest', 
    'AIResponse', 
    'AIModelType',
    'AIServiceManager',
    'DeepSeekAPIService',
    'OllamaService'
]
