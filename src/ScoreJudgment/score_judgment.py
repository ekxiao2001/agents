import asyncio
import json
from typing import Literal, Optional
import yaml

from agentscope.agent import ReActAgent
from agentscope.message import Msg
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel, DashScopeChatModel, ChatModelBase
from agentscope.formatter import DeepSeekChatFormatter, DashScopeChatFormatter, TruncatedFormatterBase

from .prompts import PROMPTS
from .schemas import ScoreJudgmentInput, ScoreJudgmentOutput, GradingCriteriaInput, GradingCriteriaOutput


class ScoreJudgmentAgent(object):
    '''分数判断器'''
    def __init__(self, model: ChatModelBase, formatter: TruncatedFormatterBase):
        """
        初始化分数判断器
        Args:
            model (ChatModelBase): 用于分数判断的模型
            formatter (TruncatedFormatterBase): 用于分数判断的格式化器
        """
        self.model = model
        self.formatter = formatter
    
    async def score_judgment(self, score_judgment_input: ScoreJudgmentInput) -> ScoreJudgmentOutput:
        """
        分数判断

        Args:
            score_judgment_input (ScoreJudgmentInput): 分数判断输入
        Returns:
            ScoreJudgmentOutput: 分数判断输出
        """

        score_gudgment_agent = ReActAgent(
            name="Agent_ScoreJudgment",
            sys_prompt=PROMPTS["score_judgment_sys_prompt"],
            formatter=self.formatter,
            model=self.model,
            memory=InMemoryMemory(),
        )

        # 若未提供判分细则，则调用判分细则生成器
        if score_judgment_input.grading_criteria == None:
            score_judgment_input.grading_criteria = await self.grading_criteria_designer(score_judgment_input)
        
        score_judgment_query = Msg(
            name="user",
            content=PROMPTS["score_judgment_query"].format(
                question_title=score_judgment_input.question_title,
                question_type=score_judgment_input.question_type,
                standard_answer=score_judgment_input.standard_answer,
                full_score=score_judgment_input.full_score,
                student_answer=score_judgment_input.student_answer,
                grading_criteria=score_judgment_input.grading_criteria,
            ),
            role="user"
        )
        res = await score_gudgment_agent(
            score_judgment_query,
            structured_model=ScoreJudgmentOutput,
        )
        score_judgment_output = ScoreJudgmentOutput(**res)
        return score_judgment_output

    async def grading_criteria_designer(self, grading_criteria_input: GradingCriteriaInput) -> str:
        """
        判分细则生成器

        Args:
            grading_criteria_input (GradingCriteriaInput): 判分细则输入
        Returns:
            str: 判分细则
        """
        grading_criteria_designer_agent = ReActAgent(
            name="Agent_GradingCriteriaDesigner",
            sys_prompt=PROMPTS["grading_criteria_designer_sys_prompt"],
            formatter=self.formatter,
            model=self.model,
            memory=InMemoryMemory(),
        )
        grading_criteria_designer_query = Msg(
            name="user",
            content=PROMPTS["grading_criteria_designer_query"].format(
                question_title=grading_criteria_input.question_title,
                question_type=grading_criteria_input.question_type,
                standard_answer=grading_criteria_input.standard_answer,
                full_score=grading_criteria_input.full_score,
            ),
            role="user"
        )
        res = await grading_criteria_designer_agent(
            grading_criteria_designer_query,
            structured_model=GradingCriteriaOutput,
        )
        grading_criteria_output = GradingCriteriaOutput(**res)

        return grading_criteria_output.grading_criteria


def build_score_judgment_agent(
    llm_binding: Literal["deepseek", "dashscope"],
    model_name: str,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    stream: bool = True,
) -> ScoreJudgmentAgent:
    try:
        if llm_binding == "deepseek":
            formatter = DeepSeekChatFormatter()
            model = OpenAIChatModel(
                model_name=model_name,
                api_key=api_key,
                stream=stream,
                client_args={"base_url": base_url},
            )
        elif llm_binding == "dashscope":
            formatter = DashScopeChatFormatter()
            model = DashScopeChatModel(
                model_name=model_name,
                api_key=api_key,
                stream=stream,
            )

        return ScoreJudgmentAgent(
            formatter=formatter,
            model=model
        )
    except Exception as e:
        raise RuntimeError(f"加载模型失败: {e}")


if __name__ == "__main__":
    # 加载配置文件
    import os
    conf_path = os.path.join(os.path.dirname(__file__), 'conf.yaml')
    with open(conf_path, 'r', encoding='utf-8') as f:
        CONF = yaml.safe_load(f)

    LLM_BINDING = CONF.get("LLM_BINDING") or os.getenv("LLM_BINDING") or "deepseek"
    MODEL_NAME = CONF.get("MODEL_NAME") or os.getenv("MODEL_NAME") or "deepseek-chat"
    API_KEY = CONF.get("API_KEY") or os.getenv("API_KEY") or ""
    BASE_URL = CONF.get("BASE_URL") or os.getenv("BASE_URL") or "https://api.deepseek.com"


    # 创建ScoreJudgmentAgent实例
    agent = build_score_judgment_agent(
        llm_binding=LLM_BINDING if LLM_BINDING in ("deepseek", "dashscope") else "deepseek",
        model_name=MODEL_NAME,
        api_key=API_KEY,
        base_url=BASE_URL,
        stream=False
    )

    # 模拟判分输入
    input = ScoreJudgmentInput(
        question_title = "请编写一个递归函数fibonacci(n)，计算斐波那契数列的第n项。斐波那契数列定义如下：\n- fibonacci(0) = 0\n- fibonacci(1) = 1\n- fibonacci(n) = fibonacci(n-1) + fibonacci(n-2) (n ≥ 2)\n\n要求：\n1. 使用递归方法实现\n2. 函数参数为整数n，返回第n项的值\n3. 处理边界情况（n < 0时返回-1）",
        question_type = "编程题",
        standard_answer = "def fibonacci(n):\n    if n < 0:\n        return -1\n    elif n == 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)",
        student_answer = "def fibonacci(n):\n    if n == 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-1)",
        full_score = 10,
        # grading_criteria = "评分细则：\n1. 函数定义正确（2分）：函数名、参数正确\n2. 递归逻辑正确（4分）：正确实现fibonacci(n) = fibonacci(n-1) + fibonacci(n-2)\n3. 边界条件处理（3分）：\n   - 正确处理n=0的情况（1分）\n   - 正确处理n=1的情况（1分）\n   - 正确处理n<0的情况（1分）\n4. 代码规范（1分）：缩进、命名规范等\n\n扣分标准：\n- 缺少边界条件处理n<0扣1分\n- 递归逻辑错误扣4分\n- 函数名或参数错误扣2分"
    )

    # 运行判断
    output = asyncio.run(agent.score_judgment(input))
    print(json.loads(output.model_dump_json()))