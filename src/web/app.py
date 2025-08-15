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
from src.services.ai.vectorizer import Vectorizer
from src.services.llm import AIServiceManager
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
                language=language if language else None,
                min_stars=min_stars if min_stars else None
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

@app.route('/vectorize', methods=['GET', 'POST'])
def vectorize():
    """向量化页面"""
    if request.method == 'POST':
        try:
            # 异步执行向量化
            result = asyncio.run(run_vectorization())
            
            if result and result.get('success'):
                flash(f'向量化成功！{result.get("message", "")}', 'success')
            else:
                flash(f'向量化失败：{result.get("message", "未知错误") if result else "未知错误"}', 'error')
                
        except Exception as e:
            flash(f'向量化出错：{str(e)}', 'error')
            logger.error(f"向量化出错: {e}")
        
        return redirect(url_for('vectorize'))
    
    return render_template('vectorize.html')

async def run_vectorization():
    """运行向量化任务"""
    database = SQLiteDatabase()
    vectorizer = Vectorizer()
    
    try:
        # 连接数据库
        if not await database.connect():
            return {"success": False, "message": "数据库连接失败"}
        
        # 初始化向量化服务
        if not await vectorizer.initialize():
            return {"success": False, "message": "向量化服务初始化失败"}
        
        # 获取所有项目数据
        projects = await database.list_projects(limit=10000, offset=0)
        
        if not projects:
            return {"success": False, "message": "没有找到项目数据"}
        
        # 转换为字典格式
        projects_data = []
        for project in projects:
            project_dict = {
                "id": project.id,
                "name": project.name,
                "full_name": project.full_name,
                "description": project.description,
                "language": project.language.value if project.language else None,
                "stars": project.stars,
                "forks": project.forks,
                "topics": project.topics,
                "created_at": project.created_at,
                "updated_at": project.updated_at
            }
            projects_data.append(project_dict)
        
        # 执行批量向量化
        result = await vectorizer.vectorize_projects_batch(projects_data)
        
        return result
        
    finally:
        await database.disconnect()
        await vectorizer.close()

@app.route('/api/vectorize', methods=['POST'])
def api_vectorize():
    """API接口：执行向量化"""
    try:
        result = asyncio.run(run_vectorization())
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': '向量化失败'}), 500
            
    except Exception as e:
        logger.error(f"API向量化失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vectorize/stats')
def api_vectorize_stats():
    """API接口：获取向量化统计信息"""
    try:
        vectorizer = Vectorizer()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 初始化向量化服务
            if not loop.run_until_complete(vectorizer.initialize()):
                return jsonify({'error': '向量化服务初始化失败'}), 500
            
            # 获取统计信息
            stats = loop.run_until_complete(vectorizer.get_vectorization_stats())
            
            # 关闭服务
            loop.run_until_complete(vectorizer.close())
            
            return jsonify(stats)
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"API获取向量化统计信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vectorize/search', methods=['POST'])
def api_vectorize_search():
    """API接口：向量搜索相似项目"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', 10)
        
        if not query:
            return jsonify({'error': '搜索关键词不能为空'}), 400
        
        vectorizer = Vectorizer()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 初始化向量化服务
            if not loop.run_until_complete(vectorizer.initialize()):
                return jsonify({'error': '向量化服务初始化失败'}), 500
            
            # 执行向量搜索
            similar_projects = loop.run_until_complete(
                vectorizer.search_similar_projects(query, top_k)
            )
            
            # 关闭服务
            loop.run_until_complete(vectorizer.close())
            
            return jsonify({
                'success': True,
                'query': query,
                'results': similar_projects,
                'total': len(similar_projects)
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"API向量搜索失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/qa')
def qa():
    """AI问答页面"""
    return render_template('qa.html')

@app.route('/api/qa/ask', methods=['POST'])
def api_qa_ask():
    """API接口：AI问答 - 集成RAG检索"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        context = data.get('context', '')
        use_rag = data.get('use_rag', True)  # 默认启用RAG
        
        if not question:
            return jsonify({'error': '问题不能为空'}), 400
        
        # 创建AI服务管理器和向量化服务
        ai_manager = AIServiceManager()
        vectorizer = Vectorizer()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 初始化AI服务
            if not loop.run_until_complete(ai_manager.initialize()):
                return jsonify({'error': 'AI服务初始化失败'}), 500
            
            # 如果启用RAG，先进行向量检索
            rag_context = ""
            if use_rag:
                try:
                    # 初始化向量化服务
                    if loop.run_until_complete(vectorizer.initialize()):
                        # 执行向量搜索，获取相关项目
                        similar_projects = loop.run_until_complete(
                            vectorizer.search_similar_projects(question, top_k=5)
                        )
                        
                        if similar_projects:
                            # 构建RAG上下文
                            rag_context = "基于您的向量库，我找到了以下相关项目信息：\n\n"
                            for i, project in enumerate(similar_projects, 1):
                                rag_context += f"{i}. **{project.get('name', 'Unknown')}**\n"
                                rag_context += f"   - 描述: {project.get('description', 'No description')}\n"
                                rag_context += f"   - 语言: {project.get('language', 'Unknown')}\n"
                                rag_context += f"   - 星数: {project.get('stars', 'Unknown')}\n"
                                rag_context += f"   - 相似度: {project.get('similarity', 'Unknown')}\n"
                                if project.get('topics'):
                                    rag_context += f"   - 标签: {', '.join(project.get('topics', []))}\n"
                                rag_context += "\n"
                            
                            logger.info(f"RAG检索到 {len(similar_projects)} 个相关项目")
                        else:
                            rag_context = "在您的向量库中没有找到直接相关的项目，我将基于通用知识为您推荐。\n\n"
                            logger.info("RAG检索未找到相关项目，使用通用知识")
                    else:
                        rag_context = "向量化服务初始化失败，我将基于通用知识为您推荐。\n\n"
                        logger.warning("向量化服务初始化失败")
                        
                except Exception as e:
                    logger.error(f"RAG检索失败: {e}")
                    rag_context = "向量检索过程中出现错误，我将基于通用知识为您推荐。\n\n"
            
            # 构建增强的系统提示词
            system_message = """你是一个专业的开源项目推荐专家。基于用户的问题和提供的项目信息，你需要：

1. 理解用户想要构建的系统类型
2. 分析提供的相关项目信息（如果有）
3. 推荐最合适的开源项目
4. 解释为什么推荐这些项目
5. 提供项目的基本信息（如技术栈、活跃度、许可证等）
6. 给出具体的使用建议和实施步骤
7. 如果提供了向量库中的项目信息，优先推荐这些项目

请用中文回答，回答要详细、专业、实用。如果提供了相关项目信息，请重点分析这些项目。"""
            
            # 合并上下文信息
            full_context = ""
            if rag_context:
                full_context += rag_context
            if context:
                full_context += f"\n用户额外需求: {context}"
            
            if full_context:
                system_message += f"\n\n上下文信息：{full_context}"
            
            # 构建用户消息
            user_message = f"我想做{question}，有什么开源项目推荐吗？请详细分析并推荐合适的项目。"
            
            # 调用AI服务
            response = loop.run_until_complete(
                ai_manager.chat(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
            )
            
            # 关闭服务
            loop.run_until_complete(ai_manager.close())
            if use_rag:
                loop.run_until_complete(vectorizer.close())
            
            if response.error:
                return jsonify({'error': f'AI回答失败: {response.error}'}), 500
            
            return jsonify({
                'success': True,
                'question': question,
                'answer': response.content,
                'model': response.model,
                'usage': response.usage,
                'rag_used': use_rag,
                'rag_context': rag_context if use_rag else ""
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"AI问答失败: {e}")
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
