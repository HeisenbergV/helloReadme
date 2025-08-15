"""
helloReadme Flask应用主文件
"""
import os
import asyncio
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text
from src.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)

from src.services.database.sqlite import SQLiteDatabase
from src.services.github.collector import GitHubCollector
from src.config.settings import settings

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 日志配置已在 src/utils/logger.py 中统一配置

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/collect', methods=['GET', 'POST'])
def collect():
    """数据采集页面"""
    if request.method == 'POST':
        collection_type = request.form.get('collection_type')
        query = request.form.get('query', '')
        language = request.form.get('language', '')
        
        # 安全地转换max_repos为整数
        try:
            max_repos_raw = request.form.get('max_repos', '100')
            max_repos = int(max_repos_raw) if max_repos_raw else 100
            # 确保值在合理范围内
            if max_repos < 1:
                max_repos = 1
            elif max_repos > 1000:
                max_repos = 1000
        except (ValueError, TypeError):
            max_repos = 100
            logger.warning(f"max_repos转换失败，使用默认值100，原始值: {request.form.get('max_repos')}")
        
        try:
            # 异步执行采集
            result = asyncio.run(run_collection(
                collection_type, query, language, max_repos
            ))
            
            if result and result.success:
                flash(f'采集成功！{result.message}', 'success')
            else:
                flash(f'采集失败：{result.message if result else "未知错误"}', 'error')
                
        except Exception as e:
            flash(f'采集出错：{str(e)}', 'error')
            logger.error(f"采集出错: {e}")
        
        return redirect(url_for('collect'))
    
    return render_template('collect.html')

async def run_collection(collection_type, query, language, max_repos):
    """运行采集任务"""
    database = SQLiteDatabase()
    try:
        if not await database.connect():
            return None
        
        collector = GitHubCollector(database)
        
        if collection_type == 'search':
            return await collector.collect_by_search(
                query=query or settings.GITHUB_SEARCH_QUERY,
                language=language,
                max_repos=max_repos
            )
        elif collection_type == 'user':
            return await collector.collect_by_user(query)
        elif collection_type == 'org':
            return await collector.collect_by_organization(query)
        else:
            return None
            
    finally:
        await database.disconnect()

@app.route('/projects')
def projects():
    """项目列表页面"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    language = request.args.get('language', '')
    min_stars = request.args.get('min_stars', type=int)
    search = request.args.get('search', '')
    
    try:
        # 同步执行数据库操作
        database = SQLiteDatabase()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if not loop.run_until_complete(database.connect()):
                flash('数据库连接失败', 'error')
                return render_template('projects.html', projects=[], pagination=None)
            
            # 构建查询参数
            query_params = {}
            if language:
                query_params['language'] = language
            if min_stars is not None and min_stars > 0:
                query_params['min_stars'] = int(min_stars)
            
            # 获取项目列表
            projects = loop.run_until_complete(database.list_projects(
                limit=per_page,
                offset=(page - 1) * per_page,
                **query_params
            ))
            
            # 获取总数
            total_count = loop.run_until_complete(database.get_project_count())
            
            # 分页信息
            pagination = {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_prev': page > 1,
                'has_next': page * per_page < total_count
            }
            
            loop.run_until_complete(database.disconnect())
            
            return render_template('projects.html', projects=projects, pagination=pagination)
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        flash(f'获取项目列表失败：{str(e)}', 'error')
        return render_template('projects.html', projects=[], pagination=None)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """项目详情页面"""
    try:
        database = SQLiteDatabase()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if not loop.run_until_complete(database.connect()):
                flash('数据库连接失败', 'error')
                return redirect(url_for('projects'))
            
            project = loop.run_until_complete(database.get_project_by_id(project_id))
            loop.run_until_complete(database.disconnect())
            
            if not project:
                flash('项目不存在', 'error')
                return redirect(url_for('projects'))
            
            return render_template('project_detail.html', project=project)
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"获取项目详情失败: {e}")
        flash(f'获取项目详情失败：{str(e)}', 'error')
        return redirect(url_for('projects'))

@app.route('/stats')
def stats():
    """统计信息页面"""
    try:
        database = SQLiteDatabase()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if not loop.run_until_complete(database.connect()):
                flash('数据库连接失败', 'error')
                return render_template('stats.html', stats={})
            
            stats = loop.run_until_complete(database.get_collection_stats())
            language_stats = loop.run_until_complete(database.get_language_stats())
            
            loop.run_until_complete(database.disconnect())
            
            return render_template('stats.html', stats=stats, language_stats=language_stats)
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        flash(f'获取统计信息失败：{str(e)}', 'error')
        return render_template('stats.html', stats={})

@app.route('/api/projects')
def api_projects():
    """API接口：获取项目列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        language = request.args.get('language', '')
        min_stars = request.args.get('min_stars', type=int)
        
        database = SQLiteDatabase()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if not loop.run_until_complete(database.connect()):
                return jsonify({'error': '数据库连接失败'}), 500
            
            # 构建查询参数
            query_params = {}
            if language:
                query_params['language'] = language
            if min_stars is not None and min_stars > 0:
                query_params['min_stars'] = int(min_stars)
            
            projects = loop.run_until_complete(database.list_projects(
                limit=per_page,
                offset=(page - 1) * per_page,
                **query_params
            ))
            
            total_count = loop.run_until_complete(database.get_project_count())
            loop.run_until_complete(database.disconnect())
            
            # 转换为JSON格式
            projects_data = []
            for project in projects:
                projects_data.append({
                    'id': project.id,
                    'name': project.name,
                    'full_name': project.full_name,
                    'description': project.description,
                    'language': project.language.value if project.language else None,
                    'stars': project.stars,
                    'forks': project.forks,
                    'topics': project.topics,
                    'created_at': project.created_at.isoformat(),
                    'updated_at': project.updated_at.isoformat()
                })
            
            return jsonify({
                'projects': projects_data,
                'total': total_count,
                'page': page,
                'per_page': per_page
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"API获取项目列表失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/collect', methods=['POST'])
def api_collect():
    """API接口：执行采集"""
    try:
        data = request.get_json()
        collection_type = data.get('type', 'search')
        query = data.get('query', '')
        language = data.get('language', '')
        max_repos = data.get('max_repos', 100)
        
        result = asyncio.run(run_collection(
            collection_type, query, language, max_repos
        ))
        
        if result:
            return jsonify({
                'success': result.success,
                'message': result.message,
                'total_collected': result.total_collected,
                'new_projects': result.new_projects,
                'updated_projects': result.updated_projects,
                'errors': result.errors
            })
        else:
            return jsonify({'error': '采集失败'}), 500
            
    except Exception as e:
        logger.error(f"API采集失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API接口：获取统计信息"""
    try:
        database = SQLiteDatabase()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if not loop.run_until_complete(database.connect()):
                return jsonify({'error': '数据库连接失败'}), 500
            
            stats = loop.run_until_complete(database.get_collection_stats())
            language_stats = loop.run_until_complete(database.get_language_stats())
            loop.run_until_complete(database.disconnect())
            
            return jsonify({
                'stats': stats,
                'language_stats': language_stats
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"API获取统计信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    # 启动应用
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=settings.DEBUG
    )
