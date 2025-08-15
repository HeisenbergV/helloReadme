"""
向量化服务
负责将项目数据转换为向量并存储到ChromaDB中
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

class Vectorizer:
    """向量化服务类"""
    
    def __init__(self):
        self.model = None
        self.client = None
        self.collection = None
        self.vector_db_path = "vector_db"
        
    async def initialize(self):
        """初始化向量化服务"""
        try:
            # 确保向量数据库目录存在
            os.makedirs(self.vector_db_path, exist_ok=True)
            
            # 初始化ChromaDB客户端
            self.client = chromadb.PersistentClient(
                path=self.vector_db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name="github_projects",
                metadata={"description": "GitHub项目向量数据库"}
            )
            
            # 加载向量模型
            logger.info(f"正在加载向量模型: {settings.VECTOR_MODEL_NAME}")
            self.model = SentenceTransformer(settings.VECTOR_MODEL_NAME)
            logger.info("向量模型加载完成")
            
            return True
            
        except Exception as e:
            logger.error(f"初始化向量化服务失败: {e}")
            return False
    
    async def vectorize_project(self, project_data: Dict[str, Any]) -> bool:
        """向量化单个项目"""
        try:
            if not self.model or not self.collection:
                logger.error("向量化服务未初始化")
                return False
            
            # 构建项目文本内容用于向量化
            project_text = self._build_project_text(project_data)
            
            # 生成向量
            embedding = self.model.encode(project_text)
            
            # 准备元数据
            metadata = {
                "project_id": project_data["id"],
                "name": project_data["name"],
                "full_name": project_data["full_name"],
                "language": project_data.get("language", ""),
                "stars": project_data.get("stars", 0),
                "forks": project_data.get("forks", 0),
                "topics": ",".join(project_data.get("topics", [])),
                "created_at": str(project_data.get("created_at", "")),
                "updated_at": str(project_data.get("updated_at", ""))
            }
            
            # 存储到向量数据库
            self.collection.add(
                embeddings=[embedding.tolist()],
                documents=[project_text],
                metadatas=[metadata],
                ids=[f"project_{project_data['id']}"]
            )
            
            logger.info(f"项目 {project_data['full_name']} 向量化成功")
            return True
            
        except Exception as e:
            logger.error(f"项目 {project_data.get('full_name', 'Unknown')} 向量化失败: {e}")
            return False
    
    async def vectorize_projects_batch(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量向量化项目"""
        try:
            if not self.model or not self.collection:
                logger.error("向量化服务未初始化")
                return {"success": False, "message": "向量化服务未初始化"}
            
            total_projects = len(projects)
            success_count = 0
            failed_count = 0
            failed_projects = []
            
            logger.info(f"开始批量向量化 {total_projects} 个项目")
            
            for project in projects:
                try:
                    # 检查项目是否已经向量化
                    existing = self.collection.get(
                        where={"project_id": project["id"]}
                    )
                    
                    if existing["ids"]:
                        logger.info(f"项目 {project['full_name']} 已存在，跳过")
                        continue
                    
                    # 向量化项目
                    if await self.vectorize_project(project):
                        success_count += 1
                    else:
                        failed_count += 1
                        failed_projects.append(project["full_name"])
                        
                except Exception as e:
                    logger.error(f"处理项目 {project.get('full_name', 'Unknown')} 时出错: {e}")
                    failed_count += 1
                    failed_projects.append(project.get("full_name", "Unknown"))
            
            logger.info(f"批量向量化完成: 成功 {success_count}, 失败 {failed_count}")
            
            return {
                "success": True,
                "message": f"批量向量化完成，成功 {success_count} 个，失败 {failed_count} 个",
                "total_projects": total_projects,
                "success_count": success_count,
                "failed_count": failed_count,
                "failed_projects": failed_projects
            }
            
        except Exception as e:
            logger.error(f"批量向量化失败: {e}")
            return {"success": False, "message": f"批量向量化失败: {str(e)}"}
    
    async def search_similar_projects(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索相似项目"""
        try:
            if not self.model or not self.collection:
                logger.error("向量化服务未初始化")
                return []
            
            # 生成查询向量
            query_embedding = self.model.encode(query)
            
            # 在向量数据库中搜索
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k
            )
            
            # 格式化结果
            similar_projects = []
            for i in range(len(results["ids"][0])):
                # 计算相似度：距离越小，相似度越高
                distance = results["distances"][0][i] if "distances" in results and results["distances"][0] else None
                
                # 将距离转换为相似度 (0-1范围)
                # 使用余弦相似度转换：similarity = 1 / (1 + distance)
                if distance is not None:
                    similarity_score = 1.0 / (1.0 + distance)
                else:
                    similarity_score = None
                
                project_info = {
                    "project_id": results["metadatas"][0][i]["project_id"],
                    "name": results["metadatas"][0][i]["name"],
                    "full_name": results["metadatas"][0][i]["full_name"],
                    "language": results["metadatas"][0][i]["language"],
                    "stars": results["metadatas"][0][i]["stars"],
                    "forks": results["metadatas"][0][i]["forks"],
                    "topics": results["metadatas"][0][i]["topics"].split(",") if results["metadatas"][0][i]["topics"] else [],
                    "similarity_score": similarity_score,
                    "distance": distance  # 保留原始距离值用于调试
                }
                similar_projects.append(project_info)
            
            return similar_projects
            
        except Exception as e:
            logger.error(f"搜索相似项目失败: {e}")
            return []
    
    async def get_vectorization_stats(self) -> Dict[str, Any]:
        """获取向量化统计信息"""
        try:
            if not self.collection:
                return {"total_vectors": 0, "collection_name": "未初始化"}
            
            count = self.collection.count()
            return {
                "total_vectors": count,
                "collection_name": self.collection.name,
                "vector_db_path": self.vector_db_path
            }
            
        except Exception as e:
            logger.error(f"获取向量化统计信息失败: {e}")
            return {"total_vectors": 0, "collection_name": "获取失败"}
    
    def _build_project_text(self, project_data: Dict[str, Any]) -> str:
        """构建用于向量化的项目文本"""
        text_parts = []
        
        # 项目名称和描述
        if project_data.get("name"):
            text_parts.append(f"项目名称: {project_data['name']}")
        
        if project_data.get("full_name"):
            text_parts.append(f"完整名称: {project_data['full_name']}")
        
        if project_data.get("description"):
            text_parts.append(f"项目描述: {project_data['description']}")
        
        # 语言和主题
        if project_data.get("language"):
            text_parts.append(f"编程语言: {project_data['language']}")
        
        if project_data.get("topics"):
            topics_text = ", ".join(project_data["topics"])
            text_parts.append(f"项目主题: {topics_text}")
        
        # 统计信息
        if project_data.get("stars"):
            text_parts.append(f"星标数: {project_data['stars']}")
        
        if project_data.get("forks"):
            text_parts.append(f"复刻数: {project_data['forks']}")
        
        # 时间信息
        if project_data.get("created_at"):
            text_parts.append(f"创建时间: {project_data['created_at']}")
        
        if project_data.get("updated_at"):
            text_parts.append(f"更新时间: {project_data['updated_at']}")
        
        return " | ".join(text_parts)
    
    async def close(self):
        """关闭向量化服务"""
        try:
            if self.client:
                # ChromaDB会自动持久化，无需手动调用persist
                logger.info("向量数据库已关闭")
        except Exception as e:
            logger.error(f"关闭向量化服务时出错: {e}")
