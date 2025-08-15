"""
helloReadme 主程序入口
"""
import asyncio
import os
from pathlib import Path
from loguru import logger

from src.services.database.sqlite import SQLiteDatabase
from src.services.github.collector import GitHubCollector
from src.config.settings import settings

async def main():
    """主函数"""
    logger.info("启动 helloReadme GitHub项目采集系统")
    
    # 初始化数据库
    logger.info("初始化数据库...")
    database = SQLiteDatabase()
    
    try:
        # 连接数据库
        if not await database.connect():
            logger.error("数据库连接失败")
            return
        
        logger.info("数据库连接成功")
        
        # 初始化GitHub采集器
        logger.info("初始化GitHub采集器...")
        collector = GitHubCollector(database)
        
        # 显示API限制信息
        rate_limit_info = collector.get_rate_limit_info()
        logger.info(f"GitHub API限制信息: {rate_limit_info}")
        
        # 开始采集AI相关项目
        logger.info("开始采集AI相关项目...")
        
        # 方式1: 通过搜索采集
        result = await collector.collect(
            type="search",
            query="AI machine learning artificial intelligence",
            language="Python",
            max_repos=50  # 限制数量，避免API限制
        )
        
        if result.success:
            logger.info(f"采集成功: {result.message}")
            logger.info(f"总计: {result.total_collected}, 新增: {result.new_projects}, 更新: {result.updated_projects}")
            
            if result.errors:
                logger.warning(f"采集过程中出现 {len(result.errors)} 个错误")
                for error in result.errors[:5]:  # 只显示前5个错误
                    logger.warning(f"  - {error}")
        else:
            logger.error(f"采集失败: {result.message}")
        
        # 显示采集统计
        stats = await database.get_collection_stats()
        logger.info(f"数据库统计: {stats}")
        
        # 列出采集的项目
        projects = await database.list_projects(limit=10)
        logger.info(f"最近采集的项目:")
        for i, project in enumerate(projects, 1):
            logger.info(f"  {i}. {project.full_name} - {project.description or '无描述'}")
        
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
    
    finally:
        # 断开数据库连接
        await database.disconnect()
        logger.info("数据库连接已断开")

if __name__ == "__main__":
    # 配置日志
    logger.add(
        settings.LOG_FILE,
        rotation="1 day",
        retention="7 days",
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )
    
    # 运行主程序
    asyncio.run(main())
