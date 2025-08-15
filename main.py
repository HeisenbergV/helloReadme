#!/usr/bin/env python3
"""
helloReadme 主启动文件
统一启动入口，启动Flask Web服务
"""
import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def main():
    """主函数"""
    try:
        from src.web.app import app
        from src.utils.logger import get_logger
        
        # 获取日志记录器
        logger = get_logger(__name__)
        
        logger.info("🚀 启动 helloReadme GitHub项目采集系统")
        logger.info("📍 访问地址: http://localhost:5000")
        logger.info("🔍 调试模式: 已启用")
        logger.info("=" * 50)
        
        # 确保必要目录存在
        os.makedirs('logs', exist_ok=True)
        os.makedirs('vector_db', exist_ok=True)
        
        # 启动Flask应用
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False  # 禁用自动重载，避免调试器问题
        )
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
