"""
DeepSeek API AI服务实现
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from src.services.llm.base import (
    AIServiceInterface, AIRequest, AIResponse, 
    AIModelType
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DeepSeekAPIService(AIServiceInterface):
    """DeepSeek API服务"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        self.base_url = base_url or os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        self.client = None
        self._available = False
        
    async def initialize(self) -> bool:
        """初始化DeepSeek API服务"""
        try:
            if not self.api_key:
                logger.error("DeepSeek API密钥未设置")
                return False
            
            # 测试API连接
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 发送测试请求
            test_payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=test_payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        self._available = True
                        logger.info("DeepSeek API服务初始化成功")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API连接测试失败: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"DeepSeek API服务初始化失败: {e}")
            return False
    
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """生成文本"""
        try:
            if not self.is_available:
                return AIResponse(
                    content="",
                    model="",
                    error="服务未初始化或不可用"
                )
            
            # 构建请求消息
            messages = []
            if request.system_message:
                messages.append({"role": "system", "content": request.system_message})
            
            # 添加上下文
            if request.context:
                for ctx in request.context:
                    if isinstance(ctx, dict) and 'role' in ctx and 'content' in ctx:
                        messages.append(ctx)
            
            # 添加用户提示
            messages.append({"role": "user", "content": request.prompt})
            
            # 调用聊天接口
            return await self.chat(messages, 
                                 temperature=request.temperature,
                                 max_tokens=request.max_tokens,
                                 model=request.model)
            
        except Exception as e:
            logger.error(f"DeepSeek API文本生成失败: {e}")
            return AIResponse(
                content="",
                model="",
                error=f"生成失败: {str(e)}"
            )
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """对话模式"""
        try:
            if not self.is_available:
                return AIResponse(
                    content="",
                    model="",
                    error="服务未初始化或不可用"
                )
            
            model = kwargs.get('model', 'deepseek-chat')
            temperature = kwargs.get('temperature', 0.7)
            max_tokens = kwargs.get('max_tokens', 1000)
            
            # 构建DeepSeek API请求
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            # 调用DeepSeek API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content']
                        
                        return AIResponse(
                            content=content,
                            model=model,
                            usage=data.get('usage', {}),
                            metadata={
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "service": "deepseek-api",
                                "base_url": self.base_url
                            }
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API调用失败: {response.status} - {error_text}")
                        return AIResponse(
                            content="",
                            model=model,
                            error=f"API调用失败: {response.status} - {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"DeepSeek API对话失败: {e}")
            return AIResponse(
                content="",
                model="",
                error=f"对话失败: {str(e)}"
            )
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "deepseek-chat",
            "deepseek-coder",
            "deepseek-chat-instruct",
            "deepseek-coder-instruct"
        ]
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息"""
        model_info = {
            "deepseek-chat": {
                "name": "DeepSeek Chat",
                "type": "chat",
                "context_length": 32768,
                "description": "通用对话模型"
            },
            "deepseek-coder": {
                "name": "DeepSeek Coder",
                "type": "code",
                "context_length": 32768,
                "description": "代码生成和编程助手"
            }
        }
        
        return model_info.get(model_name, {
            "name": model_name,
            "type": "unknown",
            "context_length": 0,
            "description": "未知模型"
        })
    
    async def close(self):
        """关闭服务"""
        self._available = False
        logger.info("DeepSeek API服务已关闭")
    
    @property
    def service_type(self) -> AIModelType:
        return AIModelType.API
    
    @property
    def is_available(self) -> bool:
        return self._available
