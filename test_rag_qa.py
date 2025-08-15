#!/usr/bin/env python3
"""
测试RAG集成的AI问答功能
"""
import asyncio
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

async def test_rag_qa():
    """测试RAG集成的AI问答功能"""
    try:
        print("🧪 测试RAG集成的AI问答功能...")
        
        # 测试配置
        from src.services.llm.config import LLMConfig
        print("✅ 配置导入成功")
        
        # 检查启用的服务
        enabled_services = LLMConfig.get_enabled_services()
        print(f"✅ 启用的服务: {enabled_services}")
        
        if not enabled_services:
            print("⚠️  没有启用的AI服务，请检查配置")
            return
        
        # 测试AI服务管理器
        from src.services.llm import AIServiceManager
        from src.services.ai.vectorizer import Vectorizer
        
        ai_manager = AIServiceManager()
        vectorizer = Vectorizer()
        
        print("✅ 服务实例创建成功")
        
        # 初始化
        success = await ai_manager.initialize()
        if success:
            print("✅ AI服务管理器初始化成功")
            
            # 测试向量化服务
            print("🔄 初始化向量化服务...")
            vectorizer_success = await vectorizer.initialize()
            if vectorizer_success:
                print("✅ 向量化服务初始化成功")
                
                # 测试RAG检索
                print("🧪 测试RAG检索...")
                question = "我想做一个在线教育平台"
                similar_projects = await vectorizer.search_similar_projects(question, top_k=3)
                
                if similar_projects:
                    print(f"✅ RAG检索成功，找到 {len(similar_projects)} 个相关项目:")
                    for i, project in enumerate(similar_projects, 1):
                        print(f"   {i}. {project.get('name', 'Unknown')}")
                        print(f"      描述: {project.get('description', 'No description')[:100]}...")
                        print(f"      相似度: {project.get('similarity', 'Unknown')}")
                else:
                    print("⚠️  RAG检索未找到相关项目")
                
                # 测试问答功能
                print("\n🧪 测试问答功能...")
                
                # 构建RAG上下文
                rag_context = ""
                if similar_projects:
                    rag_context = "基于您的向量库，我找到了以下相关项目信息：\n\n"
                    for i, project in enumerate(similar_projects, 1):
                        rag_context += f"{i}. **{project.get('name', 'Unknown')}**\n"
                        rag_context += f"   - 描述: {project.get('description', 'No description')}\n"
                        rag_context += f"   - 语言: {project.get('language', 'Unknown')}\n"
                        rag_context += f"   - 星数: {project.get('stars', 'Unknown')}\n"
                        rag_context += f"   - 相似度: {project.get('similarity', 'Unknown')}\n\n"
                
                # 构建系统提示词
                system_message = """你是一个专业的开源项目推荐专家。基于用户的问题和提供的项目信息，你需要：

1. 理解用户想要构建的系统类型
2. 分析提供的相关项目信息（如果有）
3. 推荐最合适的开源项目
4. 解释为什么推荐这些项目
5. 提供项目的基本信息（如技术栈、活跃度、许可证等）
6. 给出具体的使用建议和实施步骤
7. 如果提供了向量库中的项目信息，优先推荐这些项目

请用中文回答，回答要详细、专业、实用。如果提供了相关项目信息，请重点分析这些项目。"""
                
                if rag_context:
                    system_message += f"\n\n上下文信息：{rag_context}"
                
                # 调用AI服务
                response = await ai_manager.chat(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"我想做{question}，有什么开源项目推荐吗？请详细分析并推荐合适的项目。"}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                if response.error:
                    print(f"❌ 问答失败: {response.error}")
                else:
                    print(f"✅ 问答成功:")
                    print(f"   模型: {response.model}")
                    print(f"   回答: {response.content[:300]}...")
                    if response.usage:
                        print(f"   使用量: {response.usage}")
                
                # 关闭向量化服务
                await vectorizer.close()
                print("✅ 向量化服务已关闭")
                
            else:
                print("❌ 向量化服务初始化失败")
            
            # 关闭AI服务
            await ai_manager.close()
            print("✅ AI服务已关闭")
            
        else:
            print("❌ AI服务管理器初始化失败")
        
        print("\n🎯 所有测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 开始测试RAG集成的AI问答功能...")
    print("=" * 60)
    
    asyncio.run(test_rag_qa())
    
    print("\n" + "=" * 60)
    print("🎯 测试完成！")
