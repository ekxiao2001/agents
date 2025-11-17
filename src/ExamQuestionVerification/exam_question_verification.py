import asyncio
import json
from typing import Literal, Optional
import yaml

from agentscope.agent import ReActAgent
from agentscope.message import Msg
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel, DashScopeChatModel, ChatModelBase
from agentscope.formatter import OpenAIChatFormatter, DashScopeChatFormatter, TruncatedFormatterBase

from .prompts import PROMPTS
from .schemas import ExamQuestion, VerificationResult


class ExamQuestionVerification(object):
    '''考试题目检测+修正器'''
    def __init__(self, model: ChatModelBase, formatter: TruncatedFormatterBase):
        """
        初始化考试题目检测+修正器
        Args:
            model (ChatModelBase): 用于考试题目检测+修正的模型
            formatter (TruncatedFormatterBase): 用于考试题目检测+修正的格式化器
        """
        self.model = model
        self.formatter = formatter

    async def verify_and_fix_exam_question(self, exam_question: ExamQuestion, max_fix_attempts: int = 3) -> ExamQuestion:
        """
        主函数，用于核查和修正考试题目
        Args:
            exam_question (ExamQuestion): 考试题目信息
            max_fix_attempts (int): 最大修正次数. Defaults to 3.
        Returns:
            ExamQuestion: 最终修正后的考试题目
        """
        exam_question_history = [exam_question]
        verification_result_history = []

        for i in range(max_fix_attempts):
            # 核查考题
            print("="*20+f"第{i+1}次核查中"+"="*20)
            verification_result = await self.verify_exam_question(exam_question_history[-1])
            verification_result_history.append(verification_result)

            # 判断是否需要修正考题
            if bool(verification_result.is_compliant):
                break
            else:
                print(f"="*20+f"第{i+1}次核查，题目不合规，修正中"+"="*20)
                exam_question = await self.fix_exam_question(exam_question_history[-1], verification_result)
                exam_question_history.append(exam_question)
                print("\n")

        print("="*20+f"最终修正后的考题"+"="*20)
        print(json.dumps(exam_question_history[-1].model_dump(), indent=4, ensure_ascii=False)) # type: ignore

        return exam_question_history[-1]

    async def verify_exam_question(self, exam_question: ExamQuestion) -> VerificationResult:
        """
        核查考试题目是否合规, 若不合规, 给出修正意见

        Args:
            exam_question (ExamQuestion): 考试题目信息
        Returns:
            VerificationResult: 考试题目核查结果
        """

        agent = ReActAgent(
            name="Sub_Agent_EQV",
            sys_prompt=PROMPTS["sub_agent_verify_sys_prompt"],
            formatter=self.formatter,
            model=self.model,
            memory=InMemoryMemory(),
        )

        if exam_question.question_type == "单选题":
            verification_prompt = PROMPTS["single_choice_verification"]
        elif exam_question.question_type == "多选题":
            verification_prompt = PROMPTS["multi_choice_verification"]
        elif exam_question.question_type == "填空题":
            verification_prompt = PROMPTS["fill_blank_verification"]
        elif exam_question.question_type == "简答题":
            verification_prompt = PROMPTS["brief_answer_verification"]
        elif exam_question.question_type == "编程题":
            verification_prompt = PROMPTS["programming_verification"]
        elif exam_question.question_type == "计算题":
            verification_prompt = PROMPTS["calculation_verification"]
        else:
            verification_prompt = PROMPTS["verification_prompt"].format(
                question_type=exam_question.question_type,
            )
        verification_prompt = verification_prompt.format(
            question=exam_question.question,
            answer=exam_question.answer,
            answer_analysis=exam_question.answer_analysis,
            knowledge_point=exam_question.knowledge_point,
            knowledge_point_description=exam_question.knowledge_point_description,
            extra_requirement=exam_question.extra_requirement,
        )

        # 使用通用函数处理JSON解析重试
        json_format_prompt = """
            请严格按照以下JSON格式返回结果，不要包含任何其他文字说明：
            {
                "is_compliant": true/false,
                "suggestion": "修正建议内容"
            }
        """

        default_factory = lambda: {
            "is_compliant": False,
            "suggestion": "系统无法正确解析AI响应，请手动检查题目合规性。"
        }

        json_res = await self._call_agent_with_json_retry(
            agent=agent,
            prompt=verification_prompt,
            required_fields=["is_compliant", "suggestion"],
            default_factory=default_factory,
            max_retry_attempts=3,
            json_format_prompt=json_format_prompt
        )

        return VerificationResult(**json_res)

    async def fix_exam_question(self, exam_question: ExamQuestion, verification_result: VerificationResult) -> ExamQuestion:
        """
        基于核查结果修正考题
        Args:
            exam_question (ExamQuestion): 考试题目信息
            verification_result (VerificationResult): 考试题目核查结果

        Returns:
            ExamQuestion: 修正后的考试题目信息
        """
        if bool(verification_result.is_compliant):
            return exam_question
        else:
            agent = ReActAgent(
                name="Sub_Agent_EQF",
                sys_prompt=PROMPTS["sub_agent_fix_sys_prompt"],
                formatter=self.formatter,
                model=self.model,
                memory=InMemoryMemory(),
            )
            fix_prompt = PROMPTS["fix_prompt"].format(
                question=exam_question.question,
                answer=exam_question.answer,
                answer_analysis=exam_question.answer_analysis,
                question_type=exam_question.question_type,
                knowledge_point=exam_question.knowledge_point,
                knowledge_point_description=exam_question.knowledge_point_description,
                suggestion=verification_result.suggestion,
            )

            # 使用通用函数处理JSON解析重试
            json_format_prompt = """
                请严格按照以下JSON格式返回修正后的考题，不要包含任何其他文字说明：
                {
                    "question": "修正后的题目内容",
                    "answer": "修正后的答案内容",
                    "answer_analysis": "修正后的答案解析",
                    "question_type": "题目类型",
                    "knowledge_point": "知识点",
                    "knowledge_point_description": "知识点描述",
                    "extra_requirement": "额外要求"
                }
            """

            required_fields = ["question", "answer", "answer_analysis", "question_type",
                "knowledge_point", "knowledge_point_description", "extra_requirement"]
            default_factory = lambda: exam_question

            json_res = await self._call_agent_with_json_retry(
                agent=agent,
                prompt=fix_prompt,
                required_fields=required_fields,
                default_factory=default_factory,
                max_retry_attempts=3,
                json_format_prompt=json_format_prompt
            )

            return ExamQuestion(**json_res)

    async def _call_agent_with_json_retry(
        self,
        agent: ReActAgent,
        prompt: str,
        required_fields: list,
        default_factory: callable,
        max_retry_attempts: int = 3,
        json_format_prompt: Optional[str] = None,
    ):
        """
        通用的Agent调用和JSON解析函数

        Args:
            agent (ReActAgent): Agent实例
            prompt (str): 初始prompt内容
            required_fields (list): 必需的JSON字段列表
            default_factory (callable): 解析失败时的默认结果工厂函数
            max_retry_attempts (int): 最大重试次数
            json_format_prompt (str, optional): JSON格式提示语
            initial_attempt (int): 初始尝试次数

        Returns:
            解析后的JSON数据或默认结果
        """
        for attempt in range(max_retry_attempts):
            try:
                if attempt == 0:
                    # 第一次尝试使用原始prompt
                    res = await agent(Msg("user", role="user", content=prompt))
                else:
                    # 后续尝试要求JSON格式
                    retry_prompt = f"上一次的响应格式不正确，无法解析为JSON。{json_format_prompt}\n\n请重新回答之前的问题。"
                    res = await agent(Msg("user", role="user", content=retry_prompt))

                # 尝试解析JSON
                json_res = json.loads(res.content)

                # 验证JSON结构是否包含必要字段
                for field in required_fields:
                    if field not in json_res:
                        raise ValueError(f"JSON响应缺少 '{field}' 字段")

                # 成功解析，返回结果
                return json_res

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"第{attempt + 1}次JSON解析失败: {e}")
                print(f"Agent响应内容: {res.content}")

                if attempt == max_retry_attempts - 1:
                    # 最后一次尝试失败，返回默认结果
                    print("所有JSON解析尝试均失败，返回默认结果")
                    try:
                        return default_factory()
                    except TypeError:
                        # 兼容传入已构造好的对象
                        return default_factory
                else:
                    print(f"将进行第{attempt + 2}次重试...")
                    continue

        # 理论上不会到达这里，但为了类型安全
        try:
            return default_factory()
        except TypeError:
            return default_factory

def build_exam_verifier(
    llm_binding: Literal["openai", "dashscope"],
    model_name: str,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    stream: bool = True,
) -> ExamQuestionVerification:
    try:
        if llm_binding == "openai":
            formatter = OpenAIChatFormatter()
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

        return ExamQuestionVerification(
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


    # 创建ExamQuestionVerification实例
    verifier = build_exam_verifier(
        llm_binding=LLM_BINDING if LLM_BINDING in ("deepseek", "dashscope") else "deepseek",
        model_name=MODEL_NAME,
        api_key=API_KEY,
        base_url=BASE_URL,
        stream=False
    )

    # 模拟考试题目
    exam_question = ExamQuestion(
        question='''
        搜索算法相关\n（1）分别说明 DFS 和 BFS 如何用队列或栈实现，并对比两者遍历同一图时的顺序差异。\n（2）在求解无权图最短路径问题时，为什么 BFS 通常比 DFS 更高效？结合遍历特性解释原因。
        ''',
        answer="（1）DFS 用栈（递归或显式栈），一路深入再回溯；BFS 用队列，一层层扩展；顺序差异：DFS 纵深，BFS 横扩。\n（2）BFS 按层扩展，首次到达目标即最短路径；DFS 可能深入很长非最短路径才回溯，访问节点更多。",
        question_type="简答题",
        knowledge_point="",
        knowledge_point_description="",
        extra_requirement="将简答题修改为填空题",
    )

    # 运行考试题目核查
    new_exam_question = asyncio.run(verifier.verify_and_fix_exam_question(exam_question, max_fix_attempts=3))