"""
命令行工具
"""
import asyncio
import click
from pathlib import Path
from typing import Optional

from src.services.database.sqlite import SQLiteDatabase
from src.services.github.collector import GitHubCollector
from src.utils.logger import setup_logger, get_logger
from src.config.settings import settings

# 设置日志
setup_logger()
logger = get_logger(__name__)

@click.group()
@click.version_option(version=settings.VERSION, prog_name=settings.PROJECT_NAME)
def cli():
    """helloReadme - GitHub项目智能推荐系统"""
    pass

@cli.command()
@click.option('--query', '-q', default=settings.GITHUB_SEARCH_QUERY, help='搜索查询词')
@click.option('--language', '-l', help='编程语言过滤')
@click.option('--max-repos', '-m', default=100, help='最大采集项目数')
@click.option('--sort', default='stars', type=click.Choice(['stars', 'forks', 'updated']), help='排序方式')
@click.option('--order', default='desc', type=click.Choice(['asc', 'desc']), help='排序顺序')
def search(query: str, language: Optional[str], max_repos: int, sort: str, order: str):
    """通过搜索采集GitHub项目"""
    asyncio.run(_search_projects(query, language, max_repos, sort, order))

@cli.command()
@click.argument('username')
@click.option('--include-forks', is_flag=True, help='包含分支项目')
def user(username: str, include_forks: bool):
    """采集指定用户的项目"""
    asyncio.run(_collect_user_projects(username, include_forks))

@cli.command()
@click.argument('org_name')
@click.option('--include-forks', is_flag=True, help='包含分支项目')
def org(org_name: str, include_forks: bool):
    """采集指定组织的项目"""
    asyncio.run(_collect_org_projects(org_name, include_forks))

@cli.command()
def stats():
    """显示采集统计信息"""
    asyncio.run(_show_stats())

@cli.command()
@click.option('--limit', '-l', default=20, help='显示项目数量')
@click.option('--language', help='按语言过滤')
@click.option('--min-stars', type=int, help='最小星标数')
def list(limit: int, language: Optional[str], min_stars: Optional[int]):
    """列出已采集的项目"""
    asyncio.run(_list_projects(limit, language, min_stars))

@cli.command()
@click.argument('backup_path', type=click.Path())
def backup(backup_path: str):
    """备份数据库"""
    asyncio.run(_backup_database(backup_path))

@cli.command()
@click.argument('backup_path', type=click.Path(exists=True))
def restore(backup_path: str):
    """恢复数据库"""
    asyncio.run(_restore_database(backup_path))

async def _search_projects(query: str, language: Optional[str], max_repos: int, sort: str, order: str):
    """搜索采集项目"""
    logger.info(f"开始搜索采集: {query}")
    if language:
        logger.info(f"语言过滤: {language}")
    
    database = SQLiteDatabase()
    try:
        if not await database.connect():
            logger.error("数据库连接失败")
            return
        
        collector = GitHubCollector(database)
        result = await collector.collect_by_search(
            query=query,
            language=language,
            sort=sort,
            order=order,
            max_repos=max_repos
        )
        
        if result.success:
            logger.info(f"采集成功: {result.message}")
            logger.info(f"总计: {result.total_collected}, 新增: {result.new_projects}, 更新: {result.updated_projects}")
        else:
            logger.error(f"采集失败: {result.message}")
            
    finally:
        await database.disconnect()

async def _collect_user_projects(username: str, include_forks: bool):
    """采集用户项目"""
    logger.info(f"开始采集用户 {username} 的项目")
    
    database = SQLiteDatabase()
    try:
        if not await database.connect():
            logger.error("数据库连接失败")
            return
        
        collector = GitHubCollector(database)
        result = await collector.collect_by_user(username, include_forks)
        
        if result.success:
            logger.info(f"采集成功: {result.message}")
        else:
            logger.error(f"采集失败: {result.message}")
            
    finally:
        await database.disconnect()

async def _collect_org_projects(org_name: str, include_forks: bool):
    """采集组织项目"""
    logger.info(f"开始采集组织 {org_name} 的项目")
    
    database = SQLiteDatabase()
    try:
        if not await database.connect():
            logger.error("数据库连接失败")
            return
        
        collector = GitHubCollector(database)
        result = await collector.collect_by_organization(org_name, include_forks)
        
        if result.success:
            logger.info(f"采集成功: {result.message}")
        else:
            logger.error(f"采集失败: {result.message}")
            
    finally:
        await database.disconnect()

async def _show_stats():
    """显示统计信息"""
    database = SQLiteDatabase()
    try:
        if not await database.connect():
            logger.error("数据库连接失败")
            return
        
        stats = await database.get_collection_stats()
        logger.info("采集统计信息:")
        logger.info(f"  总项目数: {stats.get('total_projects', 0)}")
        logger.info(f"  最新采集: {stats.get('latest_collection', '无')}")
        logger.info(f"  数据库大小: {stats.get('database_size', 0)} bytes")
        
        language_stats = stats.get('languages', {})
        if language_stats:
            logger.info("  语言分布:")
            for lang, count in sorted(language_stats.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"    {lang}: {count}")
                
    finally:
        await database.disconnect()

async def _list_projects(limit: int, language: Optional[str], min_stars: Optional[int]):
    """列出项目"""
    database = SQLiteDatabase()
    try:
        if not await database.connect():
            logger.error("数据库连接失败")
            return
        
        projects = await database.list_projects(limit=limit, language=language, min_stars=min_stars)
        
        if not projects:
            logger.info("没有找到项目")
            return
        
        logger.info(f"找到 {len(projects)} 个项目:")
        for i, project in enumerate(projects, 1):
            logger.info(f"  {i}. {project.full_name}")
            logger.info(f"     描述: {project.description or '无描述'}")
            logger.info(f"     语言: {project.language.value if project.language else 'Unknown'}")
            logger.info(f"     星标: {project.stars}, 分支: {project.forks}")
            logger.info(f"     更新时间: {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("")
            
    finally:
        await database.disconnect()

async def _backup_database(backup_path: str):
    """备份数据库"""
    database = SQLiteDatabase()
    try:
        if not await database.connect():
            logger.error("数据库连接失败")
            return
        
        if await database.backup_database(backup_path):
            logger.info(f"数据库备份成功: {backup_path}")
        else:
            logger.error("数据库备份失败")
            
    finally:
        await database.disconnect()

async def _restore_database(backup_path: str):
    """恢复数据库"""
    database = SQLiteDatabase()
    try:
        if not await database.connect():
            logger.error("数据库连接失败")
            return
        
        if await database.restore_database(backup_path):
            logger.info(f"数据库恢复成功: {backup_path}")
        else:
            logger.error("数据库恢复失败")
            
    finally:
        await database.disconnect()

if __name__ == '__main__':
    cli()
