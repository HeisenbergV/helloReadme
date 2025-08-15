"""
Ollama本地模型AI服务实现
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from src.services.llm.base import (
    AIServiceInterface, AIRequest, AIResponse, 
    AIModelType
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

class OllamaService(AIServiceInterface):
    """Ollama本地模型服务"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = None
        self._available = False
        self._models = []
        
    async def initialize(self) -> bool:
        """初始化Ollama服务"""
        try:
            self.session = aiohttp.ClientSession()
            
            # 测试连接
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    self._models = [model['name'] for model in data.get('models', [])]
                    self._available = True
                    logger.info(f"Ollama服务初始化成功，可用模型: {self._models}")
                    return True
                else:
                    logger.error(f"Ollama服务连接失败: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ollama服务初始化失败: {e}")
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
                                 model=request.model)
            
        except Exception as e:
            logger.error(f"Ollama文本生成失败: {e}")
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
            
            model = kwargs.get('model', self._models[0] if self._models else 'llama2')
            temperature = kwargs.get('temperature', 0.7)
            
            # 构建Ollama API请求
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            # 调用Ollama API
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get('message', {}).get('content', '')
                    
                    return AIResponse(
                        content=content,
                        model=model,
                        usage=data.get('usage', {}),
                        metadata={
                            "temperature": temperature,
                            "service": "ollama",
                            "base_url": self.base_url
                        }
                    )
                else:
                    error_text = await response.text()
                    return AIResponse(
                        content="",
                        model=model,
                        error=f"API调用失败: {response.status} - {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Ollama对话失败: {e}")
            return AIResponse(
                content="",
                model="",
                error=f"对话失败: {str(e)}"
            )
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return self._models
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息"""
        try:
            if not self.session:
                return {"error": "服务未初始化"}
            
            async with self.session.post(
                f"{self.base_url}/api/show",
                json={"name": model_name}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "name": data.get('name', model_name),
                        "type": "local",
                        "context_length": data.get('parameters', 'unknown'),
                        "description": f"Ollama本地模型: {model_name}",
                        "size": data.get('size', 'unknown'),
                        "modified_at": data.get('modified_at', 'unknown')
                    }
                else:
                    return {
                        "name": model_name,
                        "type": "unknown",
                        "context_length": 0,
                        "description": "无法获取模型信息"
                    }
                    
        except Exception as e:
            logger.error(f"获取模型信息失败: {e}")
            return {
                "name": model_name,
                "type": "unknown",
                "context_length": 0,
                "description": f"获取信息失败: {str(e)}"
            }
    
    async def close(self):
        """关闭服务"""
        if self.session:
            await self.session.close()
        self._available = False
        logger.info("Ollama服务已关闭")
    
    @property
    def service_type(self) -> AIModelType:
        return AIModelType.LOCAL
    
    @property
    def is_available(self) -> bool:
        return self._available
