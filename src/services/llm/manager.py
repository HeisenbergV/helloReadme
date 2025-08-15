"""
AI服务管理器
支持动态切换不同的AI后端
"""
import os
from typing import Dict, List, Optional, Type, Any
from src.services.llm.base import AIServiceInterface, AIModelType
from src.services.llm.deepseek_api import DeepSeekAPIService
from src.services.llm.ollama_service import OllamaService
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AIServiceManager:
    """AI服务管理器"""
    
    def __init__(self):
        self.services: Dict[str, AIServiceInterface] = {}
        self.current_service: Optional[AIServiceInterface] = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """初始化AI服务管理器"""
        try:
            # 注册可用的AI服务
            await self._register_services()
            
            # 选择默认服务
            await self._select_default_service()
            
            self._initialized = True
            logger.info("AI服务管理器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"AI服务管理器初始化失败: {e}")
            return False
    
    async def _register_services(self):
        """注册可用的AI服务"""
        from src.services.llm.config import LLMConfig
        
        # 获取启用的服务配置
        enabled_services = LLMConfig.get_enabled_services()
        logger.info(f"启用的AI服务: {enabled_services}")
        
        # 注册DeepSeek API服务
        if 'deepseek' in enabled_services:
            from src.config.settings import settings
            deepseek_service = DeepSeekAPIService(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
            if await deepseek_service.initialize():
                self.services['deepseek'] = deepseek_service
                logger.info("DeepSeek API服务注册成功")
        
        # 注册OpenAI服务
        if 'openai' in enabled_services:
            # 这里可以添加OpenAI服务实现
            logger.info("OpenAI服务配置已启用")
        
        # 注册Anthropic服务
        if 'anthropic' in enabled_services:
            # 这里可以添加Anthropic服务实现
            logger.info("Anthropic服务配置已启用")
        
        # 注册百度文心一言服务
        if 'baidu' in enabled_services:
            # 这里可以添加百度服务实现
            logger.info("百度文心一言服务配置已启用")
        
        # 注册阿里通义千问服务
        if 'alibaba' in enabled_services:
            # 这里可以添加阿里服务实现
            logger.info("阿里通义千问服务配置已启用")
        
        # 注册智谱AI服务
        if 'zhipu' in enabled_services:
            # 这里可以添加智谱AI服务实现
            logger.info("智谱AI服务配置已启用")
        
        # 注册Ollama本地服务
        if 'ollama' in enabled_services:
            ollama_service = OllamaService()
            if await ollama_service.initialize():
                self.services['ollama'] = ollama_service
                logger.info("Ollama本地服务注册成功")
        
        logger.info(f"已注册 {len(self.services)} 个AI服务")
    
    async def _select_default_service(self):
        """选择默认AI服务"""
        from src.services.llm.config import LLMConfig
        
        # 按配置的优先级选择服务
        for service_name in LLMConfig.get_enabled_services():
            if service_name in self.services:
                self.current_service = self.services[service_name]
                logger.info(f"选择默认服务: {service_name}")
                return
        
        logger.warning("没有可用的AI服务")
    
    async def switch_service(self, service_name: str) -> bool:
        """切换AI服务"""
        try:
            if service_name not in self.services:
                logger.error(f"服务 {service_name} 不存在")
                return False
            
            # 关闭当前服务
            if self.current_service:
                await self.current_service.close()
            
            # 切换到新服务
            self.current_service = self.services[service_name]
            logger.info(f"已切换到服务: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"切换服务失败: {e}")
            return False
    
    async def get_current_service(self) -> Optional[AIServiceInterface]:
        """获取当前AI服务"""
        return self.current_service
    
    async def get_available_services(self) -> List[Dict[str, Any]]:
        """获取可用服务列表"""
        services_info = []
        for name, service in self.services.items():
            services_info.append({
                "name": name,
                "type": service.service_type.value,
                "available": service.is_available,
                "current": service == self.current_service
            })
        return services_info
    
    async def generate_text(self, prompt: str, **kwargs):
        """生成文本"""
        if not self.current_service:
            logger.error("没有可用的AI服务")
            from src.services.llm.base import AIResponse
            return AIResponse(
                content="",
                model="",
                error="没有可用的AI服务"
            )
        
        try:
            from src.services.llm.base import AIRequest
            request = AIRequest(
                prompt=prompt,
                system_message=kwargs.get('system_message'),
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens'),
                model=kwargs.get('model')
            )
            
            response = await self.current_service.generate_text(request)
            if response.error:
                logger.error(f"AI生成失败: {response.error}")
                return response  # 返回包含错误的响应对象
            
            return response
            
        except Exception as e:
            logger.error(f"生成文本失败: {e}")
            from src.services.llm.base import AIResponse
            return AIResponse(
                content="",
                model="",
                error=f"生成文本失败: {str(e)}"
            )
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs):
        """对话模式"""
        if not self.current_service:
            logger.error("没有可用的AI服务")
            from src.services.llm.base import AIResponse
            return AIResponse(
                content="",
                model="",
                error="没有可用的AI服务"
            )
        
        try:
            response = await self.current_service.chat(messages, **kwargs)
            if response.error:
                logger.error(f"AI对话失败: {response.error}")
                return response  # 返回包含错误的响应对象
            
            return response
            
        except Exception as e:
            logger.error(f"对话失败: {e}")
            from src.services.llm.base import AIResponse
            return AIResponse(
                content="",
                model="",
                error=f"对话失败: {str(e)}"
            )
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if not self.current_service:
            return []
        
        try:
            return await self.current_service.get_available_models()
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []
    
    async def close(self):
        """关闭所有服务"""
        for service_name, service in self.services.items():
            try:
                await service.close()
                logger.info(f"服务 {service_name} 已关闭")
            except Exception as e:
                logger.error(f"关闭服务 {service_name} 失败: {e}")
        
        self._initialized = False
        logger.info("AI服务管理器已关闭")
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def has_service(self) -> bool:
        return self.current_service is not None
