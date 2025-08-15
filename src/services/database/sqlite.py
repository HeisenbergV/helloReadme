"""
SQLite数据库实现
"""
import sqlite3
import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.sqlite import insert

from src.models.base import (
    GitHubProject, ProjectSearchQuery, CollectionResult, 
    ProjectLanguage, ProjectStatus
)
from src.services.database.base import DatabaseInterface
from src.config.settings import settings
from src.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)

Base = declarative_base()

class GitHubProjectTable(Base):
    """GitHub项目数据表"""
    __tablename__ = "github_projects"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(500), nullable=False, unique=True)
    description = Column(Text)
    language = Column(String(50))
    topics = Column(JSON)
    homepage = Column(String(500))
    license = Column(String(100))
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    watchers = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    pushed_at = Column(DateTime, nullable=False)
    status = Column(String(50), default="active")
    is_fork = Column(Boolean, default=False)
    is_template = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    owner_login = Column(String(255), nullable=False)
    owner_type = Column(String(50))
    default_branch = Column(String(100), default="main")
    size = Column(Integer, default=0)
    has_wiki = Column(Boolean, default=False)
    has_pages = Column(Boolean, default=False)
    readme_content = Column(Text)
    readme_encoding = Column(String(50))
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_checked = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SQLiteDatabase(DatabaseInterface):
    """SQLite数据库实现"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self._connected = False
    
    async def connect(self) -> bool:
        """连接数据库"""
        try:
            # 同步引擎用于创建表
            self.engine = create_engine(
                self.database_url,
                echo=settings.DATABASE_ECHO,
                connect_args={"check_same_thread": False}
            )
            
            # 异步引擎用于操作
            async_url = self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
            self.async_engine = create_async_engine(
                async_url,
                echo=settings.DATABASE_ECHO,
                connect_args={"check_same_thread": False}
            )
            
            # 创建会话工厂
            self.SessionLocal = sessionmaker(bind=self.engine)
            self.AsyncSessionLocal = sessionmaker(
                bind=self.async_engine, 
                class_=AsyncSession, 
                expire_on_commit=False
            )
            
            # 创建表
            await self.create_tables()
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """断开数据库连接"""
        try:
            if self.engine:
                self.engine.dispose()
            if self.async_engine:
                await self.async_engine.dispose()
            self._connected = False
            return True
        except Exception as e:
            logger.error(f"数据库断开连接失败: {e}")
            return False
    
    async def is_connected(self) -> bool:
        """检查数据库连接状态"""
        return self._connected
    
    async def create_tables(self) -> bool:
        """创建数据表"""
        try:
            Base.metadata.create_all(self.engine)
            return True
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            return False
    
    async def drop_tables(self) -> bool:
        """删除数据表"""
        try:
            Base.metadata.drop_all(self.engine)
            return True
        except Exception as e:
            logger.error(f"删除表失败: {e}")
            return False
    
    def _project_to_dict(self, project: GitHubProject) -> Dict[str, Any]:
        """将项目模型转换为字典"""
        return {
            "id": project.id,
            "name": project.name,
            "full_name": project.full_name,
            "description": project.description,
            "language": project.language.value if project.language else None,
            "topics": project.topics,
            "homepage": project.homepage,
            "license": project.license,
            "stars": project.stars,
            "forks": project.forks,
            "watchers": project.watchers,
            "open_issues": project.open_issues,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "pushed_at": project.pushed_at,
            "status": project.status.value,
            "is_fork": project.is_fork,
            "is_template": project.is_template,
            "is_archived": project.is_archived,
            "owner_login": project.owner_login,
            "owner_type": project.owner_type,
            "default_branch": project.default_branch,
            "size": project.size,
            "has_wiki": project.has_wiki,
            "has_pages": project.has_pages,
            "readme_content": project.readme_content,
            "readme_encoding": project.readme_encoding,
            "collected_at": project.collected_at,
            "last_checked": project.last_checked
        }
    
    def _detect_content_change(self, old_project: GitHubProject, new_project: GitHubProject) -> bool:
        """检测项目内容是否发生重要变更"""
        # 检测README内容变更
        if old_project.readme_content != new_project.readme_content:
            return True
        
        # 检测描述变更
        if old_project.description != new_project.description:
            return True
        
        # 检测标签变更
        if set(old_project.topics or []) != set(new_project.topics or []):
            return True
        
        # 检测语言变更
        if old_project.language != new_project.language:
            return True
        
        # 检测状态变更
        if old_project.status != new_project.status:
            return True
        
        return False
    
    def _dict_to_project(self, data: Dict[str, Any]) -> GitHubProject:
        """将字典转换为项目模型"""
        # 处理枚举类型
        language = None
        if data.get("language"):
            try:
                language = ProjectLanguage(data["language"])
            except ValueError:
                language = ProjectLanguage.OTHER
        
        status = ProjectStatus.ACTIVE
        if data.get("status"):
            try:
                status = ProjectStatus(data["status"])
            except ValueError:
                status = ProjectStatus.ACTIVE
        
        # 确保数值字段为整数类型
        def safe_int(value, default=0):
            if value is None:
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        return GitHubProject(
            id=safe_int(data["id"]),
            name=data["name"],
            full_name=data["full_name"],
            description=data.get("description"),
            language=language,
            topics=data.get("topics", []),
            homepage=data.get("homepage"),
            license=data.get("license"),
            stars=safe_int(data.get("stars"), 0),
            forks=safe_int(data.get("forks"), 0),
            watchers=safe_int(data.get("watchers"), 0),
            open_issues=safe_int(data.get("open_issues"), 0),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            pushed_at=data["pushed_at"],
            status=status,
            is_fork=bool(data.get("is_fork", False)),
            is_template=bool(data.get("is_template", False)),
            is_archived=bool(data.get("is_archived", False)),
            owner_login=data["owner_login"],
            owner_type=data.get("owner_type"),
            default_branch=data.get("default_branch", "main"),
            size=safe_int(data.get("size"), 0),
            has_wiki=bool(data.get("has_wiki", False)),
            has_pages=bool(data.get("has_pages", False)),
            readme_content=data.get("readme_content"),
            readme_encoding=data.get("readme_encoding"),
            collected_at=data.get("collected_at", datetime.now(timezone.utc)),
            last_checked=data.get("last_checked", datetime.now(timezone.utc))
        )
    
    async def save_project(self, project: GitHubProject) -> bool:
        """保存项目信息"""
        try:
            async with self.AsyncSessionLocal() as session:
                project_dict = self._project_to_dict(project)
                
                # 检查是否为更新操作
                existing_project = await self.get_project_by_id(project.id)
                is_update = existing_project is not None
                
                # 检测内容变更
                content_changed = False
                if is_update:
                    content_changed = self._detect_content_change(existing_project, project)
                
                # 使用upsert操作
                stmt = insert(GitHubProjectTable).values(**project_dict)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_=project_dict
                )
                
                await session.execute(stmt)
                await session.commit()
                
                # 记录更新信息
                if is_update and content_changed:
                    logger.info(f"项目 {project.full_name} 内容已更新，需要重新向量化")
                
                return True
                
        except Exception as e:
            logger.error(f"保存项目失败: {e}")
            return False
    
    async def get_project_by_id(self, project_id: int) -> Optional[GitHubProject]:
        """根据ID获取项目"""
        try:
            async with self.AsyncSessionLocal() as session:
                            result = await session.execute(
                GitHubProjectTable.__table__.select().where(
                    GitHubProjectTable.id == project_id
                )
            )
            row = result.fetchone()
            if row:
                try:
                    # 安全地转换行数据
                    row_dict = {}
                    for key, value in row._mapping.items():
                        row_dict[key] = value
                    return self._dict_to_project(row_dict)
                except Exception as e:
                    logger.error(f"转换行数据失败: {e}, 行: {row}")
                    return None
            return None
                
        except Exception as e:
            logger.error(f"获取项目失败: {e}")
            return None
    
    async def get_project_by_name(self, full_name: str) -> Optional[GitHubProject]:
        """根据完整名称获取项目"""
        try:
            async with self.AsyncSessionLocal() as session:
                            result = await session.execute(
                GitHubProjectTable.__table__.select().where(
                    GitHubProjectTable.full_name == full_name
                )
            )
            row = result.fetchone()
            if row:
                try:
                    # 安全地转换行数据
                    row_dict = {}
                    for key, value in row._mapping.items():
                        row_dict[key] = value
                    return self._dict_to_project(row_dict)
                except Exception as e:
                    logger.error(f"转换行数据失败: {e}, 行: {row}")
                    return None
            return None
                
        except Exception as e:
            logger.error(f"获取项目失败: {e}")
            return None
    
    async def update_project(self, project: GitHubProject) -> bool:
        """更新项目信息"""
        return await self.save_project(project)
    
    async def delete_project(self, project_id: int) -> bool:
        """删除项目"""
        try:
            async with self.AsyncSessionLocal() as session:
                await session.execute(
                    GitHubProjectTable.__table__.delete().where(
                        GitHubProjectTable.id == project_id
                    )
                )
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"删除项目失败: {e}")
            return False
    
    async def list_projects(
        self, 
        limit: int = 100, 
        offset: int = 0,
        language: Optional[str] = None,
        min_stars: Optional[int] = None
    ) -> List[GitHubProject]:
        """列出项目"""
        try:
            async with self.AsyncSessionLocal() as session:
                query = GitHubProjectTable.__table__.select()
                
                if language:
                    query = query.where(GitHubProjectTable.language == language)
                if min_stars is not None and min_stars > 0:
                    # 确保min_stars是整数类型
                    min_stars_int = int(min_stars)
                    query = query.where(GitHubProjectTable.stars >= min_stars_int)
                
                # 使用安全的排序，先按stars排序，再按id排序作为备选
                try:
                    query = query.order_by(GitHubProjectTable.stars.desc().nullslast())
                except:
                    # 如果stars排序失败，使用id排序
                    query = query.order_by(GitHubProjectTable.id.desc())
                
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                rows = result.fetchall()
                
                # 在Python中进行安全的排序
                projects = []
                for row in rows:
                    try:
                        # 安全地转换行数据
                        row_dict = {}
                        for key, value in row._mapping.items():
                            row_dict[key] = value
                        project = self._dict_to_project(row_dict)
                        projects.append(project)
                    except Exception as e:
                        logger.error(f"转换行数据失败: {e}, 行: {row}")
                        continue
                
                # 按stars进行安全排序
                def safe_sort_key(project):
                    try:
                        stars = int(project.stars) if project.stars is not None else 0
                        return stars
                    except (ValueError, TypeError):
                        return 0
                
                projects.sort(key=safe_sort_key, reverse=True)
                
                return projects
                
        except Exception as e:
            logger.error(f"列出项目失败: {e}")
            return []
    
    async def search_projects(self, query: ProjectSearchQuery) -> List[GitHubProject]:
        """搜索项目"""
        try:
            async with self.AsyncSessionLocal() as session:
                sql_query = GitHubProjectTable.__table__.select()
                
                # 简单的文本搜索
                if query.query:
                    search_term = f"%{query.query}%"
                    sql_query = sql_query.where(
                        GitHubProjectTable.description.like(search_term) |
                        GitHubProjectTable.name.like(search_term) |
                        GitHubProjectTable.topics.cast(String).like(search_term)
                    )
                
                if query.language:
                    sql_query = sql_query.where(GitHubProjectTable.language == query.language)
                
                # 排序
                if query.sort == "stars":
                    order_col = GitHubProjectTable.stars
                elif query.sort == "forks":
                    order_col = GitHubProjectTable.forks
                elif query.sort == "updated":
                    order_col = GitHubProjectTable.updated_at
                else:
                    order_col = GitHubProjectTable.stars
                
                # 使用安全的排序
                try:
                    if query.order == "desc":
                        sql_query = sql_query.order_by(order_col.desc().nullslast())
                    else:
                        sql_query = sql_query.order_by(order_col.asc().nullsfirst())
                except:
                    # 如果排序失败，使用id排序
                    sql_query = sql_query.order_by(GitHubProjectTable.id.desc())
                
                sql_query = sql_query.limit(query.per_page).offset((query.page - 1) * query.per_page)
                
                result = await session.execute(sql_query)
                rows = result.fetchall()
                
                # 在Python中进行安全的排序
                projects = []
                for row in rows:
                    try:
                        # 安全地转换行数据
                        row_dict = {}
                        for key, value in row._mapping.items():
                            row_dict[key] = value
                        project = self._dict_to_project(row_dict)
                        projects.append(project)
                    except Exception as e:
                        logger.error(f"转换行数据失败: {e}, 行: {row}")
                        continue
                
                # 按指定字段进行安全排序
                def safe_sort_key(project):
                    try:
                        if query.sort == "stars":
                            value = int(project.stars) if project.stars is not None else 0
                        elif query.sort == "forks":
                            value = int(project.forks) if project.forks is not None else 0
                        elif query.sort == "updated":
                            value = project.updated_at.timestamp() if project.updated_at else 0
                        else:
                            value = int(project.stars) if project.stars is not None else 0
                        return value
                    except (ValueError, TypeError):
                        return 0
                
                reverse = query.order == "desc"
                projects.sort(key=safe_sort_key, reverse=reverse)
                
                return projects
                
        except Exception as e:
            logger.error(f"搜索项目失败: {e}")
            return []
    
    async def get_project_count(self) -> int:
        """获取项目总数"""
        try:
            async with self.AsyncSessionLocal() as session:
                result = await session.execute(
                    GitHubProjectTable.__table__.select()
                )
                rows = result.fetchall()
                return len(rows)
                
        except Exception as e:
            logger.error(f"获取项目总数失败: {e}")
            return 0
    
    async def get_projects_by_language(self, language: str) -> List[GitHubProject]:
        """根据语言获取项目"""
        return await self.list_projects(limit=1000, language=language)
    
    async def get_projects_by_topic(self, topic: str) -> List[GitHubProject]:
        """根据标签获取项目"""
        try:
            async with self.AsyncSessionLocal() as session:
                result = await session.execute(
                    GitHubProjectTable.__table__.select().where(
                        GitHubProjectTable.topics.contains([topic])
                    )
                )
                rows = result.fetchall()
                
                projects = []
                for row in rows:
                    try:
                        # 安全地转换行数据
                        row_dict = {}
                        for key, value in row._mapping.items():
                            row_dict[key] = value
                        project = self._dict_to_project(row_dict)
                        projects.append(project)
                    except Exception as e:
                        logger.error(f"转换行数据失败: {e}, 行: {row}")
                        continue
                
                return projects
                
        except Exception as e:
            logger.error(f"根据标签获取项目失败: {e}")
            return []
    
    async def batch_save_projects(self, projects: List[GitHubProject]) -> bool:
        """批量保存项目"""
        try:
            async with self.AsyncSessionLocal() as session:
                updated_projects = []
                new_projects = []
                
                for project in projects:
                    # 检查是否为更新操作
                    existing_project = await self.get_project_by_id(project.id)
                    if existing_project:
                        # 检测内容变更
                        if self._detect_content_change(existing_project, project):
                            updated_projects.append(project)
                            logger.info(f"项目 {project.full_name} 内容已更新，需要重新向量化")
                    else:
                        new_projects.append(project)
                    
                    # 执行upsert操作
                    project_dict = self._project_to_dict(project)
                    stmt = insert(GitHubProjectTable).values(**project_dict)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["id"],
                        set_=project_dict
                    )
                    await session.execute(stmt)
                
                await session.commit()
                
                # 记录统计信息
                if updated_projects:
                    logger.info(f"批量保存完成: {len(new_projects)} 个新项目, {len(updated_projects)} 个更新项目")
                else:
                    logger.info(f"批量保存完成: {len(new_projects)} 个新项目")
                
                return True
                
        except Exception as e:
            logger.error(f"批量保存项目失败: {e}")
            return False
    
    async def batch_update_projects(self, projects: List[GitHubProject]) -> bool:
        """批量更新项目"""
        return await self.batch_save_projects(projects)
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """获取采集统计信息"""
        try:
            async with self.AsyncSessionLocal() as session:
                total_count = await self.get_project_count()
                
                # 获取最新采集时间
                result = await session.execute(
                    GitHubProjectTable.__table__.select(
                        GitHubProjectTable.collected_at
                    ).order_by(GitHubProjectTable.collected_at.desc()).limit(1)
                )
                latest_collection = result.scalar()
                
                # 获取语言统计
                language_stats = await self.get_language_stats()
                
                return {
                    "total_projects": total_count,
                    "latest_collection": latest_collection.isoformat() if latest_collection else None,
                    "languages": language_stats,
                    "database_size": Path(self.database_url.replace("sqlite:///", "")).stat().st_size if "sqlite:///" in self.database_url else 0
                }
                
        except Exception as e:
            logger.error(f"获取采集统计信息失败: {e}")
            return {}
    
    async def get_language_stats(self) -> Dict[str, int]:
        """获取语言统计信息"""
        try:
            async with self.AsyncSessionLocal() as session:
                # 使用原生SQL查询语言统计
                sql = """
                SELECT language, COUNT(*) as count 
                FROM github_projects 
                GROUP BY language
                """
                result = await session.execute(text(sql))
                rows = result.fetchall()
                return {row.language or "Unknown": row.count for row in rows}
                
        except Exception as e:
            logger.error(f"获取语言统计信息失败: {e}")
            return {}
    
    async def get_projects_needing_vectorization(self, limit: int = 100) -> List[GitHubProject]:
        """获取需要重新向量化的项目（内容已更新但向量未更新）"""
        try:
            # 这里可以添加一个字段来标记向量化状态
            # 暂时返回所有项目，后续可以优化
            return await self.list_projects(limit=limit)
        except Exception as e:
            logger.error(f"获取需要向量化的项目失败: {e}")
            return []
    
    async def mark_project_vectorized(self, project_id: int) -> bool:
        """标记项目已完成向量化"""
        try:
            async with self.AsyncSessionLocal() as session:
                # 这里可以添加一个字段来标记向量化状态
                # 暂时只记录日志
                logger.info(f"项目 {project_id} 已标记为向量化完成")
                return True
        except Exception as e:
            logger.error(f"标记项目向量化状态失败: {e}")
            return False
    
    async def get_topic_stats(self) -> Dict[str, int]:
        """获取标签统计信息"""
        try:
            # 这个实现比较复杂，需要展开JSON数组
            # 简化实现：返回空字典
            return {}
        except Exception as e:
            logger.error(f"获取标签统计信息失败: {e}")
            return {}
    
    async def export_data(self, format: str = "json") -> str:
        """导出数据"""
        try:
            projects = await self.list_projects(limit=10000)
            if format == "json":
                return json.dumps([project.dict() for project in projects], ensure_ascii=False, indent=2)
            else:
                return str(projects)
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            return ""
    
    async def import_data(self, data: str, format: str = "json") -> bool:
        """导入数据"""
        try:
            if format == "json":
                projects_data = json.loads(data)
                projects = [GitHubProject(**project_data) for project_data in projects_data]
                return await self.batch_save_projects(projects)
            else:
                return False
        except Exception as e:
            logger.error(f"导入数据失败: {e}")
            return False
    
    async def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            import shutil
            db_path = self.database_url.replace("sqlite:///", "")
            shutil.copy2(db_path, backup_path)
            return True
        except Exception as e:
            logger.error(f"备份数据库失败: {e}")
            return False
    
    async def restore_database(self, backup_path: str) -> bool:
        """恢复数据库"""
        try:
            import shutil
            db_path = self.database_url.replace("sqlite:///", "")
            shutil.copy2(backup_path, db_path)
            return True
        except Exception as e:
            logger.error(f"恢复数据库失败: {e}")
            return False
