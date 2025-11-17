import sys, asyncio
import datetime
import json
from typing import Dict, List, Optional

from agentscope.model import OpenAIChatModel, DashScopeChatModel
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter, DashScopeChatFormatter
from agentscope.message import Msg
from src.exam_generation.prompts import (
    knowledge_sys_prompt,
    questions_by_knowledge_prompt,
    questions_by_description_prompt,
    questions_combined_prompt,
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


class KnowledgeBasedQuestionGenerator:
    """基于知识点的考题生成器"""
    
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


    def create_agent(self):
        """创建新的Agent实例"""
        sys_prompt = knowledge_sys_prompt()
        
        return ReActAgent(
            name="KnowledgeBasedQuestionGenerator",
            sys_prompt=sys_prompt,
            model=self.model,
            formatter=self.formatter,
        )

    async def generate_questions(self, topic: str = "", knowledge_points: Optional[List[str]] = None, 
                                question_type: str = "", count: int = 0, description: str = "") -> str:
        """根据知识点和需求描述生成考题"""
        print(f"[INFO] 开始生成考题")
        if topic:
            print(f"[INFO] 课程: 《{topic}》")
        if knowledge_points:
            print(f"[INFO] 知识点: {', '.join(knowledge_points)}")
        if question_type:
            print(f"[INFO] 题型: {question_type}")
        if count > 0:
            print(f"[INFO] 数量: {count}")
        if description:
            print(f"[INFO] 需求描述: {description}")
            
        try:
            # 直接将所有输入发送给大模型，让大模型判断如何处理
            questions_content = await self._generate_questions_by_combined_input(
                topic, knowledge_points or [], question_type, count, description
            )
            print(f"[SUCCESS] 考题生成成功")
            return questions_content
        except Exception as e:
            print(f"[ERROR] 考题生成失败: {type(e).__name__}: {e}")
            return f"考题生成失败: {type(e).__name__}: {str(e)}"
    
    async def _generate_questions_by_knowledge(self, topic: str, knowledge_points: List[str], question_type: str, count: int) -> str:
        """根据知识点生成考题"""
        prompt = questions_by_knowledge_prompt(topic, knowledge_points, question_type, count)
        
        return await self._call_api_with_retry(prompt, topic, knowledge_points, question_type, count)
    
    async def _generate_questions_by_description(self, description: str) -> str:
        """根据需求描述生成考题"""
        prompt = questions_by_description_prompt(description)
        
        return await self._call_api_with_retry(prompt)

    async def _generate_questions_by_combined_input(self, topic: str, knowledge_points: List[str], 
                                                  question_type: str, count: int, description: str) -> str:
        """根据结构化输入和自定义描述结合生成考题"""
        prompt = questions_combined_prompt(topic, knowledge_points, question_type, count, description)
        
        return await self._call_api_with_retry(prompt)
    
    async def _call_api_with_retry(self, prompt: str, topic: str = "", knowledge_points: Optional[List[str]] = None, 
                                  question_type: str = "", count: int = 0, max_retries: int = 3) -> str:
        """带重试的API调用"""
        for attempt in range(max_retries):
            try:
                print(f"[DEBUG] 考题生成 (第{attempt+1}次尝试)")
                
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
    print("=== 考题生成系统 ===")
    
    # 创建考题生成器实例
    question_generator = KnowledgeBasedQuestionGenerator()
    
    # 只保留混合输入方式
    print("\n请先输入课程相关信息：")
    topic = get_valid_input("请输入课程名称: ")
    
    print("\n请输入知识点（输入空行结束）:")
    i = 1
    knowledge_points = []  # 初始化知识点列表
    while True:
        kp = input(f"  知识点{i}: ").strip()
        if not kp:
            if i == 1:
                print("至少需要输入一个知识点。")
                continue
            else:
                break
        knowledge_points.append(kp)
        i += 1
        
    question_type = get_valid_input("请输入题型（如：选择题、简答题、计算题等）: ")
    count = get_valid_integer("请输入题目数量: ")
    
    # 添加难度分级选择
    print("\n请选择难度等级:")
    print("1. 简单")
    print("2. 较易")
    print("3. 一般")
    print("4. 较难")
    print("5. 困难")
    
    difficulty_levels = ["简单", "较易", "一般", "较难", "困难"]
    while True:
        difficulty_choice = input("请输入选项 (1-5): ").strip()
        if difficulty_choice in ["1", "2", "3", "4", "5"]:
            difficulty = difficulty_levels[int(difficulty_choice) - 1]
            break
        else:
            print("请输入有效的选项 (1-5)。")
    
    print("\n请直接输入您的需求描述（可选，如果提供将与上述配置结合使用，冲突部分以描述为准）：")
    print("例如：'请为《算法设计与分析》课程生成1道关于动态规划的选择题'")
    description = input("\n请输入需求描述（可留空）: ").strip()
    
    # 显示输入的信息供用户确认
    print(f"\n🎯 输入信息确认:")
    print(f"   课程: 《{topic}》")
    print(f"   知识点: {', '.join(knowledge_points)}")
    print(f"   题型: {question_type}")
    print(f"   数量: {count}道")
    print(f"   难度: {difficulty}")
    if description:
        print(f"   需求描述: {description}")
    
    # 构建最终描述
    structured_description = f"请为《{topic}》课程生成{count}道{question_type}，难度为{difficulty}，基于以下知识点：{', '.join(knowledge_points)}"
    
    print(f"\n🎯 最终生成配置:")
    print(f"   课程: 《{topic}》")
    print(f"   知识点: {', '.join(knowledge_points)}")
    print(f"   题型: {question_type}")
    print(f"   数量: {count}道")
    print(f"   难度: {difficulty}")
    if description:
        print(f"   用户自定义描述: {description}")
        print(f"   ⚠️  冲突处理策略: 冲突部分以用户自定义描述为准")
    
    try:
        # 生成考题
        print("\n📝 开始生成考题...")
        questions_content = await question_generator.generate_questions(
            topic, knowledge_points, question_type, count, description
        )
        
        if questions_content.startswith("考题生成失败:"):
            print(f"❌ 考题生成失败: {questions_content}")
            return
        
        # 保存考题
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if description:
            questions_filename = f"考题_需求描述_{timestamp}.json"
        else:
            questions_filename = f"考题_{topic}_{question_type}_{timestamp}.json"
        try:
            with open(questions_filename, 'w', encoding='utf-8') as f:
                f.write(questions_content)
            print(f"✅ 考题已保存到文件: {questions_filename}")
        except Exception as e:
            print(f"⚠️ 保存考题文件失败: {e}")
            return
            
        print("\n🎉 考题生成完成!")

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