"""
AI服务抽象基类
定义统一的AI服务接口，支持多种后端
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

class AIModelType(Enum):
    """AI模型类型"""
    API = "api"           # API调用
    LOCAL = "local"       # 本地模型
    HYBRID = "hybrid"     # 混合模式

@dataclass
class AIRequest:
    """AI请求参数"""
    prompt: str
    system_message: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    model: Optional[str] = None
    context: Optional[List[Dict[str, Any]]] = None

@dataclass
class AIResponse:
    """AI响应结果"""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AIServiceInterface(ABC):
    """AI服务接口抽象基类"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化AI服务"""
        pass
    
    @abstractmethod
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """生成文本"""
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """对话模式"""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        pass
    
    @abstractmethod
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭服务"""
        pass
    
    @property
    @abstractmethod
    def service_type(self) -> AIModelType:
        """服务类型"""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """服务是否可用"""
        pass
