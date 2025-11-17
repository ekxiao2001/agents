import sys, asyncio
import datetime
import json
from typing import Dict, List, Optional


from agentscope.model import OpenAIChatModel, DashScopeChatModel
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter, DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from src.exam_generation.prompts import (
    multi_type_sys_prompt,
    paper_generation_prompt,
    answers_generation_prompt,
)


# 加载配置文件
import os
import yaml
conf_path = os.path.join(os.path.dirname(__file__), 'conf.yaml')
with open(conf_path, 'r', encoding='utf-8') as f:
    CONF = yaml.safe_load(f)

LLM_BINDING = CONF.get("LLM_BINDING") or os.getenv("LLM_BINDING") or "deepseek"
MODEL_NAME = CONF.get("MODEL_NAME") or os.getenv("MODEL_NAME") or "deepseek-chat"
API_KEY = CONF.get("API_KEY") or os.getenv("API_KEY") or ""
BASE_URL = CONF.get("BASE_URL") or os.getenv("BASE_URL") or "https://api.deepseek.com"


class MultiTypePaperGenerator:
    """多题型试卷生成器 - 支持多种题型的试卷生成"""
    
    def __init__(self):
        if LLM_BINDING == "openai":
            self.formatter = OpenAIChatFormatter()
            self.model = OpenAIChatModel(
                model_name=MODEL_NAME,
                api_key=API_KEY,
                stream=False,
                client_args={"base_url": BASE_URL},
            )
        elif LLM_BINDING == "dashscope":
            self.formatter = DashScopeChatFormatter()
            self.model = DashScopeChatModel(
                model_name=MODEL_NAME,
                api_key=API_KEY,
                stream=False,
            )
        # 创建缓存内存实例，用于存储用户输入的缓存信息
        self.cache_memory = InMemoryMemory()

    def create_agent(self):
        """创建新的Agent实例"""
        sys_prompt = multi_type_sys_prompt()
        return ReActAgent(
            name="MultiTypePaperGenerator",
            sys_prompt=sys_prompt,
            model=self.model,
            formatter=self.formatter,
            memory=InMemoryMemory()
        )

    async def generate_full_paper(self, topic: str, question_types: List[Dict]) -> tuple[str, str]:
        """生成包含多种题型的完整试卷和答案"""
        print(f"[INFO] 生成《{topic}》课程试卷")
        print(f"[INFO] 题型配置:")
        total_score = 0
        for qt in question_types:
            section_score = qt['count'] * qt['score']
            total_score += section_score
            print(f"  {qt['index']}. {qt['type']} ({qt['count']}道 × {qt['score']}分 = {section_score}分)")
        print(f"  总分: {total_score}分")
        
        try:
            # 生成完整试卷
            paper_content = await self._generate_paper(topic, question_types)
            
            # 生成答案解析
            answer_content = await self._generate_answers(paper_content)
            
            print(f"[SUCCESS] 试卷和答案生成成功")
            return paper_content, answer_content
            
        except Exception as e:
            print(f"[ERROR] 试卷生成失败: {type(e).__name__}: {e}")
            # 返回错误信息
            error_msg = f"试卷生成失败: {type(e).__name__}: {str(e)}"
            return error_msg, error_msg
    
    async def _generate_paper(self, topic: str, question_types: List[Dict]) -> str:
        """生成完整试卷"""
        # 构建题型说明
        type_descriptions = []
        total_score = 0
        for qt in question_types:
            section_score = qt['count'] * qt['score']
            total_score += section_score
            type_descriptions.append(f"{qt['index']}. {qt['type']}：{qt['count']}道，每道{qt['score']}分，共{section_score}分")
        
        prompt = paper_generation_prompt(topic, type_descriptions, total_score)
        return await self._call_api_with_retry(prompt)
    
    async def _generate_answers(self, paper_content: str) -> str:
        """生成答案解析"""
        prompt = answers_generation_prompt(paper_content)
        return await self._call_api_with_retry(prompt)
    
    async def _call_api_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """带重试的API调用（使用AgentScope）"""
        for attempt in range(max_retries):
            try:
                print(f"[DEBUG] 试卷生成 (第{attempt+1}次尝试)")
                
                # 创建新的Agent实例
                agent = self.create_agent()
                
                # 发送消息
                msg = Msg(name="user", content=prompt, role="user")
                response = await agent.reply(msg)
                
                # 提取内容
                result = str(response.content) if hasattr(response, 'content') else str(response)
                
                if result and len(result.strip()) > 10:
                    print(f"[SUCCESS] 生成成功 ({len(result)}个字符)")
                    return result
                else:
                    print(f"[ERROR] 生成失败 (第{attempt+1}次): 返回内容为空")
                    
            except Exception as e:
                print(f"[ERROR] 生成失败 (第{attempt+1}次): {type(e).__name__}: {e}")
                if attempt == max_retries - 1:
                    # 最后一次尝试失败，返回错误信息而不是抛出异常
                    return f"生成失败: {type(e).__name__}: {str(e)}"
                # 等待2秒再重试
                await asyncio.sleep(2)
        
        # 这行代码理论上不会执行到，但为了类型安全添加
        return "生成失败: 未知错误"

    async def cache_user_input(self, topic: str, question_types: List[Dict]):
        """缓存用户输入信息到AgentScope内存"""
        cache_data = {
            "topic": topic,
            "question_types": question_types,
            "timestamp": datetime.datetime.now().isoformat()
        }
        cache_key = f"cache_{topic}_paper"
        await self.cache_memory.add(Msg(name=cache_key, content=json.dumps(cache_data), role="system"))
        print(f"[CACHE] 已缓存用户输入: {cache_key}")

    async def get_cached_input(self, topic: str) -> Optional[Dict]:
        """从AgentScope内存中获取缓存的用户输入"""
        cache_key = f"cache_{topic}_paper"
        memory_content = await self.cache_memory.get_memory()
        
        for item in memory_content:
            if hasattr(item, 'name') and item.name == cache_key:
                try:
                    # 确保content是字符串类型
                    content_str = str(item.content) if not isinstance(item.content, str) else item.content
                    cache_data = json.loads(content_str)
                    print(f"[CACHE] 找到缓存: {cache_key}")
                    return cache_data
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        print(f"[CACHE] 未找到缓存: {cache_key}")
        return None


def get_valid_input(prompt: str, error_msg: str = "输入不能为空，请重新输入。") -> str:
    """获取非空用户输入"""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print(error_msg)


def get_valid_integer(prompt: str, error_msg: str = "请输入有效的数字。") -> int:
    """获取有效的整数输入"""
    while True:
        try:
            value = input(prompt).strip()
            if value:
                return int(value)
            print("输入不能为空，请重新输入。")
        except ValueError:
            print(error_msg)


async def main():
    """主程序入口"""
    print("=== 多题型试卷生成系统 ===")
    
    # 创建试卷生成器实例
    paper_generator = MultiTypePaperGenerator()
    
    # 缓存用户输入的信息
    cached_topic = ""
    cached_question_types = []
    
    while True:
        try:
            # 获取课程名称
            if cached_topic:
                topic_input = input(f"请输入课程名称 (直接回车使用'{cached_topic}'): ").strip()
                if not topic_input:
                    topic = cached_topic
                else:
                    topic = topic_input
            else:
                topic = get_valid_input("请输入课程名称: ")
            
            print("\n请设置试卷的题型、数量和分值（输入空题型名称结束输入）:")
            question_types = []
            index = 1
            
            # 如果有缓存的题型，先显示并询问是否使用
            if cached_question_types:
                print(f"\n已缓存的题型配置:")
                total_score = 0
                for qt in cached_question_types:
                    section_score = qt['count'] * qt['score']
                    total_score += section_score
                    print(f"   {qt['index']}. {qt['type']}: {qt['count']}道 × {qt['score']}分 = {section_score}分")
                
                use_cached = input("是否使用缓存的题型配置？(y/N): ").strip().lower()
                if use_cached == 'y' or use_cached == 'yes':
                    question_types = cached_question_types
                    # 更新课程名称缓存
                    cached_topic = topic
                    # 直接进入最终确认环节
                    break
            
            while True:
                print(f"\n第{index}种题型:")
                qt_type = input("  题型名称（如：选择题、填空题、简答题等，直接回车结束）: ").strip()
                
                # 如果题型名称为空，结束输入
                if not qt_type:
                    if index == 1:
                        print("  至少需要设置一种题型，请继续输入。")
                        continue
                    else:
                        break
                
                # 获取题目数量和每题分值
                count = get_valid_integer("  题目数量: ")
                score = get_valid_integer("  每题分值: ")
                
                # 显示输入的信息供用户确认
                print(f"\n🎯 第{index}种题型信息确认:")
                print(f"   题型名称: {qt_type}")
                print(f"   题目数量: {count}")
                print(f"   每题分值: {score}")
                
                # 询问用户是否正确
                confirm = input("以上信息是否正确？(Y/n): ").strip().lower()
                if confirm == '' or confirm == 'y' or confirm == 'yes':
                    # 添加到题型列表
                    question_types.append({
                        "index": str(index),  # 直接使用数字
                        "type": qt_type,
                        "count": count,
                        "score": score
                    })
                    index += 1
                else:
                    print("请重新输入该题型信息。")
                    continue
            
            if not question_types:
                print("未设置任何题型，程序退出。")
                return
            
            # 缓存输入的信息
            cached_topic = topic
            cached_question_types = question_types
            break  # 跳出外层循环，进入最终确认
            
        except KeyboardInterrupt:
            print("\n用户中断操作")
            return
        except Exception as e:
            print(f"发生未知错误: {e}")
            return
    
    # 显示最终生成配置并确认
    while True:
        print(f"\n🎯 最终生成配置:")
        print(f"   课程: 《{topic}》")
        total_score = 0
        for qt in question_types:
            section_score = qt['count'] * qt['score']
            total_score += section_score
            print(f"   {qt['index']}. {qt['type']}: {qt['count']}道 × {qt['score']}分 = {section_score}分")
        print(f"   总分: {total_score}分")
        
        # 询问用户是否正确
        confirm = input("\n以上配置是否正确？(Y/n): ").strip().lower()
        if confirm == '' or confirm == 'y' or confirm == 'yes':
            break
        else:
            # 如果配置不正确，让用户选择要修改的部分
            print("\n请选择要修改的部分:")
            print("1. 课程名称")
            print("2. 题型配置")
            print("3. 重新输入所有信息")
            
            try:
                choice = input("请输入选择 (1-3): ").strip()
                if choice == "1":
                    topic = get_valid_input("请输入课程名称: ")
                    # 更新缓存
                    cached_topic = topic
                elif choice == "2":
                    # 不清空题型列表，而是读取缓存进行修改
                    # 如果有缓存的题型，先显示并允许用户修改
                    if cached_question_types:
                        print(f"\n当前题型配置:")
                        for i, qt in enumerate(cached_question_types, 1):
                            print(f"  {i}. {qt['type']}: {qt['count']}道 × {qt['score']}分")
                        
                        # 询问用户是否要修改现有题型
                        modify_existing = input("是否要修改现有题型？(y/N): ").strip().lower()
                        if modify_existing == 'y' or modify_existing == 'yes':
                            # 让用户选择要修改哪个题型
                            while True:
                                try:
                                    selected_index = input("请选择要修改的题型编号 (输入题型前的数字，多个编号用逗号分隔，或输入'all'修改所有): ").strip()
                                    if selected_index.lower() == 'all':
                                        # 修改所有题型
                                        question_types = []
                                        for i, qt in enumerate(cached_question_types, 1):
                                            print(f"\n修改第{i}种题型:")
                                            print(f"  当前题型: {qt['type']}")
                                            new_type = input(f"  题型名称 (直接回车使用'{qt['type']}'): ").strip()
                                            if not new_type:
                                                new_type = qt['type']
                                            
                                            print(f"  当前数量: {qt['count']}")
                                            new_count_input = input(f"  题目数量 (直接回车使用'{qt['count']}'): ").strip()
                                            new_count = int(new_count_input) if new_count_input and new_count_input.isdigit() else qt['count']
                                            
                                            print(f"  当前分值: {qt['score']}")
                                            new_score_input = input(f"  每题分值 (直接回车使用'{qt['score']}'): ").strip()
                                            new_score = int(new_score_input) if new_score_input and new_score_input.isdigit() else qt['score']
                                            
                                            # 添加到题型列表
                                            question_types.append({
                                                "index": str(i),
                                                "type": new_type,
                                                "count": new_count,
                                                "score": new_score
                                            })
                                        break  # 完成所有题型修改
                                    elif selected_index:
                                        # 解析用户输入的编号
                                        selected_indices = []
                                        for idx_str in selected_index.split(','):
                                            idx_str = idx_str.strip()
                                            if idx_str.isdigit():
                                                idx = int(idx_str)
                                                if 1 <= idx <= len(cached_question_types):
                                                    selected_indices.append(idx)
                                                else:
                                                    print(f"无效的题型编号: {idx}，请重新输入。")
                                                    raise ValueError("Invalid index")
                                            else:
                                                print(f"无效的输入: {idx_str}，请输入数字。")
                                                raise ValueError("Invalid input")
                                        
                                        # 修改选定的题型
                                        question_types = []
                                        for i, qt in enumerate(cached_question_types, 1):
                                            if i in selected_indices:
                                                print(f"\n修改第{i}种题型:")
                                                print(f"  当前题型: {qt['type']}")
                                                new_type = input(f"  题型名称 (直接回车使用'{qt['type']}'): ").strip()
                                                if not new_type:
                                                    new_type = qt['type']
                                                
                                                print(f"  当前数量: {qt['count']}")
                                                new_count_input = input(f"  题目数量 (直接回车使用'{qt['count']}'): ").strip()
                                                new_count = int(new_count_input) if new_count_input and new_count_input.isdigit() else qt['count']
                                                
                                                print(f"  当前分值: {qt['score']}")
                                                new_score_input = input(f"  每题分值 (直接回车使用'{qt['score']}'): ").strip()
                                                new_score = int(new_score_input) if new_score_input and new_score_input.isdigit() else qt['score']
                                                
                                                # 添加到题型列表
                                                question_types.append({
                                                    "index": str(i),
                                                    "type": new_type,
                                                    "count": new_count,
                                                    "score": new_score
                                                })
                                            else:
                                                # 保留未修改的题型
                                                question_types.append(qt)
                                        break  # 完成选定题型修改
                                    else:
                                        print("输入不能为空，请重新输入。")
                                except ValueError:
                                    continue  # 重新输入
                                except Exception as e:
                                    print(f"输入处理错误: {e}，请重新输入。")
                                    continue  # 重新输入
                        else:
                            # 保持原有题型配置
                            question_types = cached_question_types
                    else:
                        # 如果没有缓存，重新输入题型
                        question_types = []
                        index = 1
                        while True:
                            print(f"\n第{index}种题型:")
                            qt_type = input("  题型名称（如：选择题、填空题、简答题等，直接回车结束）: ").strip()
                            
                            # 如果题型名称为空，结束输入
                            if not qt_type:
                                if index == 1:
                                    print("  至少需要设置一种题型，请继续输入。")
                                    continue
                                else:
                                    break
                            
                            # 获取题目数量和每题分值
                            count = get_valid_integer("  题目数量: ")
                            score = get_valid_integer("  每题分值: ")
                            
                            # 显示输入的信息供用户确认
                            print(f"\n🎯 第{index}种题型信息确认:")
                            print(f"   题型名称: {qt_type}")
                            print(f"   题目数量: {count}")
                            print(f"   每题分值: {score}")
                            
                            # 询问用户是否正确
                            confirm = input("以上信息是否正确？(Y/n): ").strip().lower()
                            if confirm == '' or confirm == 'y' or confirm == 'yes':
                                # 添加到题型列表
                                question_types.append({
                                    "index": str(index),  # 直接使用数字
                                    "type": qt_type,
                                    "count": count,
                                    "score": score
                                })
                                index += 1
                            else:
                                print("请重新输入该题型信息。")
                                continue
                    # 更新缓存
                    cached_question_types = question_types
                elif choice == "3":
                    # 重新输入所有信息，跳出内层循环，重新开始外层循环
                    cached_topic = ""
                    cached_question_types = []
                    break
            except Exception as e:
                print(f"输入处理错误: {e}，请重新输入所有信息。")
                # 重新输入所有信息
                cached_topic = ""
                cached_question_types = []
                break
    
    # 如果用户选择重新输入所有信息，继续外层循环
    if not cached_topic and not cached_question_types:
        return await main()  # 重新开始
    
    # 缓存输入的信息
    await paper_generator.cache_user_input(topic, question_types)
    
    try:
        # 生成试卷和答案
        print("\n📝 开始生成试卷和答案...")
        paper_content, answer_content = await paper_generator.generate_full_paper(topic, question_types)
        
        if paper_content.startswith("试卷生成失败:"):
            print(f"❌ 试卷生成失败: {paper_content}")
            return
        
        # 保存试卷
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        paper_filename = f"试卷_{topic}_{timestamp}.md"
        try:
            with open(paper_filename, 'w', encoding='utf-8') as f:
                f.write(paper_content)
            print(f"✅ 试卷已保存到文件: {paper_filename}")
        except Exception as e:
            print(f"⚠️ 保存试卷文件失败: {e}")
            return
        
        # 保存答案
        answer_filename = f"试卷答案_{topic}_{timestamp}.md"
        try:
            with open(answer_filename, 'w', encoding='utf-8') as f:
                f.write(answer_content)
            print(f"✅ 答案已保存到文件: {answer_filename}")
        except Exception as e:
            print(f"⚠️ 保存答案文件失败: {e}")
        
        print("\n🎉 试卷生成完成!")

    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"❌ 程序运行错误: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())