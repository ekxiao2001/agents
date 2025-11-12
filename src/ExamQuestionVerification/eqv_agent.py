from agentscope.message._message_base import Msg
import asyncio
import os
import yaml

from agentscope.agent import ReActAgent
from agentscope.message import Msg, TextBlock
from agentscope.memory import InMemoryMemory, MemoryBase
from agentscope.model import OpenAIChatModel, DashScopeChatModel, ChatModelBase
from agentscope.formatter import DeepSeekChatFormatter, DashScopeChatFormatter, TruncatedFormatterBase
from agentscope.tool import Toolkit, ToolResponse


from .exam_question_verification import ExamQuestionVerification
from .prompts import PROMPTS
from .schemas import ExamQuestion, VerificationResult

# import agentscope
# agentscope.init(studio_url="http://localhost:3000")


class ExamQuestionVerificationAgent(ReActAgent):
    def __init__(
        self,
        name: str,
        model: ChatModelBase,
        memory: MemoryBase,
        formatter: TruncatedFormatterBase,
        toolkit: Toolkit | None = None,
        sys_prompt: str = PROMPTS["plan_agent_sys_prompt"],
        max_iters: int = 10,
    ) -> None:
        # 先调用父类初始化，避免在调用前设置任何属性
        tools = toolkit or Toolkit()
        super().__init__(
            name=name,
            model=model,
            memory=memory,
            formatter=formatter,
            toolkit=tools,
            sys_prompt=sys_prompt,
            max_iters=max_iters,
        )

        self.formatter = formatter
        self.model = model

        self.verifier = ExamQuestionVerification(
            model=model,
            formatter=formatter,
        )

        # 注册工具到当前 Agent 的 toolkit
        self.toolkit.register_tool_function(self.exam_question_verify_tool)
        self.toolkit.register_tool_function(self.exam_question_fix_tool)

    async def exam_question_verify_tool(
        self,
        question: str,
        answer: str,
        answer_analysis: str,
        question_type: str,
        knowledge_point: str,
        knowledge_point_description: str,
        extra_requirement: str,
    ) -> ToolResponse:
        """
        核查考试题目是否合规, 若不合规, 给出修正意见(工具函数)

        Args:
            question (str): 考试题目
            answer (str): 考试题目答案
            answer_analysis (str): 考试题目答案解析
            question_type (str): 考试题目类型
            knowledge_point (str): 考试题目所属的知识点
            knowledge_point_description (str): 考试题目所属的知识点的具体描述
            extra_requirement (str): 考试题目额外要求
        """
        try:
            verification_result = await self.verifier.verify_exam_question(ExamQuestion(
                question=question,
                answer=answer,
                answer_analysis=answer_analysis,
                question_type=question_type,
                knowledge_point=knowledge_point,
                knowledge_point_description=knowledge_point_description,
                extra_requirement=extra_requirement,
            ))
            # transform verification_result to json string
            verification_result_json = verification_result.model_dump_json()
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"考试题目核查成功！核查结果：\n{verification_result_json}"
                    ),
                ],
            )
        except Exception as e:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"核查工具调用中断，错误信息：{str(e)}",
                    ),
                ],
            )

    async def exam_question_fix_tool(
        self,
        question: str,
        answer: str,
        answer_analysis: str,
        question_type: str,
        knowledge_point: str,
        knowledge_point_description: str,
        extra_requirement: str,
        suggestion: str,
    ) -> ToolResponse:
        """
        基于修正意见，修正考题(工具函数)

        Args:
            question (str): 考试题目
            answer (str): 考试题目答案
            answer_analysis (str): 考试题目答案解析
            question_type (str): 考试题目类型
            knowledge_point (str): 考试题目所属的知识点
            knowledge_point_description (str): 考试题目所属的知识点的具体描述
            extra_requirement (str): 考试题目额外要求
            suggestion (str): 考题修正意见
        """

        try:
            fixed_question = await self.verifier.fix_exam_question(
                ExamQuestion(
                question=question,
                answer=answer,
                answer_analysis=answer_analysis,
                question_type=question_type,
                knowledge_point=knowledge_point,
                knowledge_point_description=knowledge_point_description,
                extra_requirement=extra_requirement,
                ),
                VerificationResult(
                    is_compliant=False,
                    suggestion=suggestion,
                )
            )
            # transform fixed_question to json string
            fixed_question_json = fixed_question.model_dump_json()
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"考题修正成功！修正后的考题信息：\n{fixed_question_json}",
                    ),
                ],
            )
        except Exception as e:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"修正工具调用中断，错误信息：{str(e)}",
                    ),
                ],
            )

    

async def main():

    conf_path = os.path.join(os.path.dirname(__file__), "conf.yaml")
    with open(conf_path, "r", encoding="utf-8") as f:
        CONF = yaml.safe_load(f)

    LLM_BINDING = CONF.get("LLM_BINDING") or os.getenv("LLM_BINDING") or "deepseek"
    MODEL_NAME = CONF.get("MODEL_NAME") or os.getenv("MODEL_NAME") or "deepseek-chat"
    API_KEY = CONF.get("API_KEY") or os.getenv("API_KEY") or ""
    BASE_URL = CONF.get("BASE_URL") or os.getenv("BASE_URL") or "https://api.deepseek.com"
    if LLM_BINDING == "deepseek":
        model = OpenAIChatModel(
            model_name=MODEL_NAME,
            api_key=API_KEY,
            client_args={"base_url": BASE_URL},
            stream=True,
        )
        formatter = DeepSeekChatFormatter()
    elif LLM_BINDING == "dashscope":
        model = DashScopeChatModel(
            model_name=MODEL_NAME,
            api_key=API_KEY,
            stream=True,
        )
        formatter = DashScopeChatFormatter()
    else:
        raise ValueError(f"不支持的LLM绑定: {LLM_BINDING}")

    agent = ExamQuestionVerificationAgent(
        name="考试题目核查代理",
        model=model,
        formatter=formatter,
        memory=InMemoryMemory()
    )

    exam_question = ExamQuestion(
        question='''
        搜索算法相关\n（1）分别说明 DFS 和 BFS 如何用队列或栈实现，并对比两者遍历同一图时的顺序差异。\n（2）在求解无权图最短路径问题时，为什么 BFS 通常比 DFS 更高效？结合遍历特性解释原因。
        ''',
        answer="（1）DFS 用栈（递归或显式栈），一路深入再回溯；BFS 用队列，一层层扩展；顺序差异：DFS 纵深，BFS 横扩。\n（2）BFS 按层扩展，首次到达目标即最短路径；DFS 可能深入很长非最短路径才回溯，访问节点更多。",
        answer_analysis="",
        question_type="简答题",
        knowledge_point="",
        knowledge_point_description="",
        extra_requirement="将简答题修改为填空题",
    )


    # query = '''
    # 仅核查考题：
    # 考试题目：{question}
    # 考题答案：{answer}
    # 考题答案解析：{answer_analysis}
    # 考试题目类型：{question_type}
    # 考试题目所属的知识点：{knowledge_point}
    # 考试题目所属的知识点的具体描述：{knowledge_point_description}
    # 考试题目额外要求：{extra_requirement}
    # '''.format(**exam_question.model_dump())

    # res = await agent.reply(
    #     Msg("user", role="user", content=query),
    #     # structured_model=ExamQuestion,
    # )
    # print("="*20+f"修正后的考题信息"+"="*20)
    # print(res.content)

    async def run_conversation(agent: ReActAgent) -> None:
        from agentscope.agent import UserAgent
        user = UserAgent(name="user")
        msg = None
        while True:
            msg = await user(msg)
            if msg.get_text_content() == "exit":
                break
            msg = await agent(msg)

    await run_conversation(agent=agent)
    

if __name__ == "__main__":
    asyncio.run(main())