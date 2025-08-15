"""
抽象数据库接口
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.models.base import GitHubProject, ProjectSearchQuery, CollectionResult

class DatabaseInterface(ABC):
    """数据库接口抽象类"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接数据库"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """断开数据库连接"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """检查数据库连接状态"""
        pass
    
    @abstractmethod
    async def create_tables(self) -> bool:
        """创建数据表"""
        pass
    
    @abstractmethod
    async def drop_tables(self) -> bool:
        """删除数据表"""
        pass
    
    # GitHub项目相关操作
    @abstractmethod
    async def save_project(self, project: GitHubProject) -> bool:
        """保存项目信息"""
        pass
    
    @abstractmethod
    async def get_project_by_id(self, project_id: int) -> Optional[GitHubProject]:
        """根据ID获取项目"""
        pass
    
    @abstractmethod
    async def get_project_by_name(self, full_name: str) -> Optional[GitHubProject]:
        """根据完整名称获取项目"""
        pass
    
    @abstractmethod
    async def update_project(self, project: GitHubProject) -> bool:
        """更新项目信息"""
        pass
    
    @abstractmethod
    async def delete_project(self, project_id: int) -> bool:
        """删除项目"""
        pass
    
    @abstractmethod
    async def list_projects(
        self, 
        limit: int = 100, 
        offset: int = 0,
        language: Optional[str] = None,
        min_stars: Optional[int] = None
    ) -> List[GitHubProject]:
        """列出项目"""
        pass
    
    @abstractmethod
    async def search_projects(
        self, 
        query: ProjectSearchQuery
    ) -> List[GitHubProject]:
        """搜索项目"""
        pass
    
    @abstractmethod
    async def get_project_count(self) -> int:
        """获取项目总数"""
        pass
    
    @abstractmethod
    async def get_projects_by_language(self, language: str) -> List[GitHubProject]:
        """根据语言获取项目"""
        pass
    
    @abstractmethod
    async def get_projects_by_topic(self, topic: str) -> List[GitHubProject]:
        """根据标签获取项目"""
        pass
    
    # 批量操作
    @abstractmethod
    async def batch_save_projects(self, projects: List[GitHubProject]) -> bool:
        """批量保存项目"""
        pass
    
    @abstractmethod
    async def batch_update_projects(self, projects: List[GitHubProject]) -> bool:
        """批量更新项目"""
        pass
    
    # 统计信息
    @abstractmethod
    async def get_collection_stats(self) -> Dict[str, Any]:
        """获取采集统计信息"""
        pass
    
    @abstractmethod
    async def get_language_stats(self) -> Dict[str, int]:
        """获取语言统计信息"""
        pass
    
    @abstractmethod
    async def get_topic_stats(self) -> Dict[str, int]:
        """获取标签统计信息"""
        pass
    
    # 数据迁移
    @abstractmethod
    async def export_data(self, format: str = "json") -> str:
        """导出数据"""
        pass
    
    @abstractmethod
    async def import_data(self, data: str, format: str = "json") -> bool:
        """导入数据"""
        pass
    
    @abstractmethod
    async def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        pass
    
    @abstractmethod
    async def restore_database(self, backup_path: str) -> bool:
        """恢复数据库"""
        pass
