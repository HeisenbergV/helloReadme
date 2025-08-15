"""
GitHub项目采集器
"""
import asyncio
import time
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timezone
from github import Github, GithubException
from github.Repository import Repository
from github.PaginatedList import PaginatedList

from src.models.base import (
    GitHubProject, ProjectSearchQuery, CollectionResult,
    ProjectLanguage, ProjectStatus
)
from src.services.database.base import DatabaseInterface
from src.config.settings import settings
from src.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)

class DataSourceCollector:
    """数据源采集器抽象基类"""
    
    def __init__(self, database: DatabaseInterface):
        self.database = database
        self.collection_stats = {
            "total_collected": 0,
            "new_projects": 0,
            "updated_projects": 0,
            "errors": []
        }
    
    async def collect(self, **kwargs) -> CollectionResult:
        """采集数据"""
        raise NotImplementedError
    
    async def _save_project(self, project: GitHubProject) -> bool:
        """保存项目到数据库"""
        try:
            # 检查项目是否已存在
            existing_project = await self.database.get_project_by_id(project.id)
            
            if existing_project:
                # 更新现有项目
                if await self.database.update_project(project):
                    self.collection_stats["updated_projects"] += 1
                    return True
            else:
                # 保存新项目
                if await self.database.save_project(project):
                    self.collection_stats["new_projects"] += 1
                    return True
            
            return False
            
        except Exception as e:
            error_msg = f"保存项目 {project.full_name} 失败: {e}"
            logger.error(error_msg)
            self.collection_stats["errors"].append(error_msg)
            return False
    
    async def _batch_save_projects(self, projects: List[GitHubProject]) -> bool:
        """批量保存项目"""
        try:
            # 分离新项目和更新项目
            new_projects = []
            update_projects = []
            
            for project in projects:
                existing_project = await self.database.get_project_by_id(project.id)
                if existing_project:
                    update_projects.append(project)
                else:
                    new_projects.append(project)
            
            # 批量保存
            if new_projects:
                await self.database.batch_save_projects(new_projects)
                self.collection_stats["new_projects"] += len(new_projects)
            
            if update_projects:
                await self.database.batch_update_projects(update_projects)
                self.collection_stats["updated_projects"] += len(update_projects)
            
            self.collection_stats["total_collected"] += len(projects)
            return True
            
        except Exception as e:
            error_msg = f"批量保存项目失败: {e}"
            logger.error(error_msg)
            self.collection_stats["errors"].append(error_msg)
            return False
    
    def _get_collection_result(self, success: bool, message: str) -> CollectionResult:
        """生成采集结果"""
        return CollectionResult(
            success=success,
            total_collected=self.collection_stats["total_collected"],
            new_projects=self.collection_stats["new_projects"],
            updated_projects=self.collection_stats["updated_projects"],
            errors=self.collection_stats["errors"],
            message=message
        )

class GitHubCollector(DataSourceCollector):
    """GitHub项目采集器"""
    
    def __init__(self, database: DatabaseInterface, github_token: str = None):
        super().__init__(database)
        self.github_token = github_token or settings.GITHUB_TOKEN
        self.github_client = None
        self._init_github_client()
    
    def _init_github_client(self):
        """初始化GitHub客户端"""
        try:
            if self.github_token:
                self.github_client = Github(self.github_token)
                logger.info("使用GitHub Token初始化客户端")
            else:
                self.github_client = Github()
                logger.warning("未提供GitHub Token，使用匿名访问（限制较多）")
        except Exception as e:
            logger.error(f"初始化GitHub客户端失败: {e}")
            self.github_client = None
    
    def _clean_readme_content(self, content: str) -> str:
        """清理README内容，移除图片、HTML标签等，只保留纯文本"""
        if not content:
            return ""
        
        import re
        
        # 移除Markdown图片语法 ![alt](url) 和 ![alt](url "title")
        content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', content)
        
        # 移除Markdown链接语法 [text](url)，但保留文本
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        
        # 移除HTML图片标签 <img src="..." alt="..." />
        content = re.sub(r'<img[^>]+>', '', content)
        
        # 移除HTML标签，但保留内容
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除Markdown表格语法
        content = re.sub(r'\|[^|]*\|[^|]*\|', '', content)
        content = re.sub(r'\|[-|]+\|', '', content)
        
        # 移除Markdown代码块标记（保留代码内容）
        content = re.sub(r'^```\w*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```$', '', content, flags=re.MULTILINE)
        
        # 移除Markdown行内代码标记（保留代码内容）
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # 移除Markdown粗体和斜体标记（保留文本内容）
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^*]+)\*', r'\1', content)
        content = re.sub(r'__([^_]+)__', r'\1', content)
        content = re.sub(r'_([^_]+)_', r'\1', content)
        
        # 移除Markdown删除线标记
        content = re.sub(r'~~([^~]+)~~', r'\1', content)
        
        # 移除Markdown引用标记
        content = re.sub(r'^>\s*', '', content, flags=re.MULTILINE)
        
        # 移除Markdown水平线
        content = re.sub(r'^[-*_]{3,}$', '', content, flags=re.MULTILINE)
        
        # 移除多余的空白行
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # 移除行首行尾空白
        content = content.strip()
        
        return content
    
    def _repository_to_project(self, repo: Repository) -> GitHubProject:
        """将GitHub仓库对象转换为项目模型"""
        try:
            # 获取README内容
            readme_content = None
            readme_encoding = None
            try:
                readme = repo.get_readme()
                raw_content = readme.decoded_content.decode('utf-8')
                readme_encoding = 'utf-8'
                
                # 清理README内容，移除图片和HTML标签，只保留纯文本
                readme_content = self._clean_readme_content(raw_content)
                
            except Exception as e:
                logger.warning(f"获取README失败: {e}")
                pass
            
            # 确定项目状态
            status = ProjectStatus.ACTIVE
            if repo.archived:
                status = ProjectStatus.ARCHIVED
            elif repo.fork:
                status = ProjectStatus.FORKED
            elif repo.is_template:
                status = ProjectStatus.TEMPLATE
            
            # 确定编程语言
            language = ProjectLanguage.OTHER
            if repo.language:
                try:
                    language = ProjectLanguage(repo.language)
                except ValueError:
                    language = ProjectLanguage.OTHER
            
            return GitHubProject(
                id=repo.id,
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description,
                language=language,
                topics=repo.get_topics() if repo.has_issues else [],
                homepage=repo.homepage,
                license=repo.license.name if repo.license else None,
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                watchers=repo.watchers_count,
                open_issues=repo.open_issues_count,
                created_at=repo.created_at,
                updated_at=repo.updated_at,
                pushed_at=repo.pushed_at,
                status=status,
                is_fork=repo.fork,
                is_template=repo.is_template,
                is_archived=repo.archived,
                owner_login=repo.owner.login,
                owner_type=repo.owner.type,
                default_branch=repo.default_branch,
                size=repo.size,
                has_wiki=repo.has_wiki,
                has_pages=repo.has_pages,
                readme_content=readme_content,
                readme_encoding=readme_encoding,
                collected_at=datetime.now(timezone.utc),
                last_checked=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"转换仓库 {repo.full_name} 失败: {e}")
            raise
    
    async def collect_by_search(
        self, 
        query: str = None, 
        language: str = None,
        sort: str = "stars",
        order: str = "desc",
        max_repos: int = None
    ) -> CollectionResult:
        """通过搜索采集项目"""
        try:
            if not self.github_client:
                return self._get_collection_result(False, "GitHub客户端未初始化")
            
            search_query = query or settings.GITHUB_SEARCH_QUERY
            if language:
                search_query += f" language:{language}"
            
            # 确保max_repos是整数
            if max_repos is None:
                max_repos = settings.GITHUB_MAX_REPOS
            else:
                try:
                    max_repos = int(max_repos)
                    if max_repos < 1:
                        max_repos = 1
                    elif max_repos > 1000:
                        max_repos = 1000
                except (ValueError, TypeError):
                    max_repos = settings.GITHUB_MAX_REPOS
                    logger.warning(f"max_repos类型错误，使用默认值: {settings.GITHUB_MAX_REPOS}")
            
            logger.info(f"开始搜索GitHub项目: {search_query}")
            logger.info(f"最大采集数量: {max_repos}")
            
            # 执行搜索
            repositories = self.github_client.search_repositories(
                query=search_query,
                sort=sort,
                order=order
            )
            
            collected_projects = []
            total_count = min(repositories.totalCount, max_repos)
            
            logger.info(f"找到 {total_count} 个项目，开始采集...")
            
            for i, repo in enumerate(repositories[:max_repos]):
                try:
                    # 转换项目模型
                    project = self._repository_to_project(repo)
                    collected_projects.append(project)
                    
                    # 每采集一定数量后保存一次
                    if len(collected_projects) >= settings.COLLECTION_BATCH_SIZE:
                        await self._batch_save_projects(collected_projects)
                        collected_projects = []
                        logger.info(f"已采集 {i + 1}/{total_count} 个项目")
                    
                    # 控制请求频率
                    await asyncio.sleep(settings.GITHUB_RATE_LIMIT_DELAY)
                    
                except Exception as e:
                    error_msg = f"采集项目 {repo.full_name} 失败: {e}"
                    logger.error(error_msg)
                    self.collection_stats["errors"].append(error_msg)
                    continue
            
            # 保存剩余项目
            if collected_projects:
                await self._batch_save_projects(collected_projects)
            
            message = f"成功采集 {self.collection_stats['total_collected']} 个项目，新增 {self.collection_stats['new_projects']} 个，更新 {self.collection_stats['updated_projects']} 个"
            logger.info(message)
            
            return self._get_collection_result(True, message)
            
        except Exception as e:
            error_msg = f"搜索采集失败: {e}"
            logger.error(error_msg)
            self.collection_stats["errors"].append(error_msg)
            return self._get_collection_result(False, error_msg)
    
    async def collect_by_user(
        self, 
        username: str,
        include_forks: bool = False
    ) -> CollectionResult:
        """采集指定用户的项目"""
        try:
            if not self.github_client:
                return self._get_collection_result(False, "GitHub客户端未初始化")
            
            logger.info(f"开始采集用户 {username} 的项目")
            
            user = self.github_client.get_user(username)
            repositories = user.get_repos()
            
            collected_projects = []
            
            for repo in repositories:
                try:
                    # 跳过分支项目（如果不需要）
                    if not include_forks and repo.fork:
                        continue
                    
                    project = self._repository_to_project(repo)
                    collected_projects.append(project)
                    
                    # 批量保存
                    if len(collected_projects) >= settings.COLLECTION_BATCH_SIZE:
                        await self._batch_save_projects(collected_projects)
                        collected_projects = []
                    
                    await asyncio.sleep(settings.GITHUB_RATE_LIMIT_DELAY)
                    
                except Exception as e:
                    error_msg = f"采集项目 {repo.full_name} 失败: {e}"
                    logger.error(error_msg)
                    self.collection_stats["errors"].append(error_msg)
                    continue
            
            # 保存剩余项目
            if collected_projects:
                await self._batch_save_projects(collected_projects)
            
            message = f"成功采集用户 {username} 的 {self.collection_stats['total_collected']} 个项目"
            logger.info(message)
            
            return self._get_collection_result(True, message)
            
        except Exception as e:
            error_msg = f"采集用户项目失败: {e}"
            logger.error(error_msg)
            self.collection_stats["errors"].append(error_msg)
            return self._get_collection_result(False, error_msg)
    
    async def collect_by_organization(
        self, 
        org_name: str,
        include_forks: bool = False
    ) -> CollectionResult:
        """采集指定组织的项目"""
        try:
            if not self.github_client:
                return self._get_collection_result(False, "GitHub客户端未初始化")
            
            logger.info(f"开始采集组织 {org_name} 的项目")
            
            org = self.github_client.get_organization(org_name)
            repositories = org.get_repos()
            
            collected_projects = []
            
            for repo in repositories:
                try:
                    # 跳过分支项目（如果不需要）
                    if not include_forks and repo.fork:
                        continue
                    
                    project = self._repository_to_project(repo)
                    collected_projects.append(project)
                    
                    # 批量保存
                    if len(collected_projects) >= settings.COLLECTION_BATCH_SIZE:
                        await self._batch_save_projects(collected_projects)
                        collected_projects = []
                    
                    await asyncio.sleep(settings.GITHUB_RATE_LIMIT_DELAY)
                    
                except Exception as e:
                    error_msg = f"采集项目 {repo.full_name} 失败: {e}"
                    logger.error(error_msg)
                    self.collection_stats["errors"].append(error_msg)
                    continue
            
            # 保存剩余项目
            if collected_projects:
                await self._batch_save_projects(collected_projects)
            
            message = f"成功采集组织 {org_name} 的 {self.collection_stats['total_collected']} 个项目"
            logger.info(message)
            
            return self._get_collection_result(True, message)
            
        except Exception as e:
            error_msg = f"采集组织项目失败: {e}"
            logger.error(error_msg)
            self.collection_stats["errors"].append(error_msg)
            return self._get_collection_result(False, error_msg)
    
    async def collect(self, **kwargs) -> CollectionResult:
        """通用采集方法"""
        collection_type = kwargs.get("type", "search")
        
        if collection_type == "search":
            return await self.collect_by_search(**kwargs)
        elif collection_type == "user":
            return await self.collect_by_user(**kwargs)
        elif collection_type == "organization":
            return await self.collect_by_organization(**kwargs)
        else:
            return self._get_collection_result(False, f"不支持的采集类型: {collection_type}")
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """获取API限制信息"""
        try:
            if not self.github_client:
                return {"error": "GitHub客户端未初始化"}
            
            rate_limit = self.github_client.get_rate_limit()
            return {
                "core": {
                    "limit": rate_limit.core.limit,
                    "remaining": rate_limit.core.remaining,
                    "reset": rate_limit.core.reset.isoformat() if rate_limit.core.reset else None
                },
                "search": {
                    "limit": rate_limit.search.limit,
                    "remaining": rate_limit.search.remaining,
                    "reset": rate_limit.search.reset.isoformat() if rate_limit.search.reset else None
                }
            }
        except Exception as e:
            return {"error": str(e)}
