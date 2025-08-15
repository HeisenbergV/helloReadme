"""
LLM服务配置
"""
from typing import Dict, Any
from src.config.settings import settings

class LLMConfig:
    """LLM服务配置类"""
    
    # 服务优先级配置
    SERVICE_PRIORITY = ["ollama", "deepseek", "openai", "anthropic", "baidu", "alibaba", "zhipu"]
    
    @classmethod
    def get_service_config(cls, service_name: str) -> Dict[str, Any]:
        """获取指定服务的配置"""
        configs = {
            'deepseek': {
                'api_key': settings.DEEPSEEK_API_KEY,
                'base_url': settings.DEEPSEEK_BASE_URL,
                'enabled': bool(settings.DEEPSEEK_API_KEY)
            },
            'openai': {
                'api_key': settings.OPENAI_API_KEY,
                'base_url': settings.OPENAI_BASE_URL,
                'enabled': bool(settings.OPENAI_API_KEY)
            },
            'anthropic': {
                'api_key': settings.ANTHROPIC_API_KEY,
                'base_url': settings.ANTHROPIC_BASE_URL,
                'enabled': bool(settings.ANTHROPIC_API_KEY)
            },
            'baidu': {
                'api_key': settings.BAIDU_API_KEY,
                'secret_key': settings.BAIDU_SECRET_KEY,
                'base_url': settings.BAIDU_BASE_URL,
                'enabled': bool(settings.BAIDU_API_KEY and settings.BAIDU_SECRET_KEY)
            },
            'alibaba': {
                'api_key': settings.ALIBABA_API_KEY,
                'base_url': settings.ALIBABA_BASE_URL,
                'enabled': bool(settings.ALIBABA_API_KEY)
            },
            'zhipu': {
                'api_key': settings.ZHIPU_API_KEY,
                'base_url': settings.ZHIPU_BASE_URL,
                'enabled': bool(settings.ZHIPU_API_KEY)
            },
            'ollama': {
                'base_url': settings.OLLAMA_BASE_URL,
                'enabled': True  # Ollama默认启用
            }
        }
        
        return configs.get(service_name, {})
    
    @classmethod
    def get_enabled_services(cls) -> list:
        """获取启用的服务列表"""
        enabled = []
        for service in cls.SERVICE_PRIORITY:
            config = cls.get_service_config(service)
            if config.get('enabled', False):
                enabled.append(service)
        return enabled
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'model': settings.DEFAULT_LLM_MODEL,
            'temperature': settings.DEFAULT_LLM_TEMPERATURE,
            'max_tokens': settings.DEFAULT_LLM_MAX_TOKENS
        }
