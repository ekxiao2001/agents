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
from .schemas import ExamSettingsInput, ExamSettingsOutput


class ExamSettingsExtractionAgent(object):
    '''考试设置提取器'''
    def __init__(self, model: ChatModelBase, formatter: TruncatedFormatterBase):
        """
        初始化考试设置提取器
        Args:
            model (ChatModelBase): 用于考试设置提取的模型
            formatter (TruncatedFormatterBase): 用于考试设置提取的格式化器
        """
        self.model = model
        self.formatter = formatter

    async def extract_settings(self, exam_settings_input: ExamSettingsInput) -> ExamSettingsOutput:
        """
        提取考试设置信息

        Args:
            exam_settings_input (ExamSettingsInput): 考试设置提取输入
        Returns:
            ExamSettingsOutput: 考试设置提取输出
        """
        exam_settings_extraction_agent = ReActAgent(
            name="Agent_ExamSettingsExtraction",
            sys_prompt=PROMPTS["exam_settings_extraction_sys_prompt"],
            formatter=self.formatter,
            model=self.model,
            memory=InMemoryMemory(),
        )

        exam_settings_extraction_query = Msg(
            name="user",
            content=PROMPTS["exam_settings_extraction_query"].format(
                text_content=exam_settings_input.text_content,
            ),
            role="user"
        )

        res = await exam_settings_extraction_agent(
            exam_settings_extraction_query,
            structured_model=ExamSettingsOutput,
        )

        exam_settings_output = ExamSettingsOutput(**res.metadata)
        return exam_settings_output


def build_exam_settings_agent(
    llm_binding: Literal["deepseek", "dashscope"],
    model_name: str,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    stream: bool = True,
) -> ExamSettingsExtractionAgent:
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

        return ExamSettingsExtractionAgent(
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


    # 创建ExamSettingsExtractionAgent实例
    agent = build_exam_settings_agent(
        llm_binding=LLM_BINDING if LLM_BINDING in ("deepseek", "dashscope") else "deepseek",
        model_name=MODEL_NAME,
        api_key=API_KEY,
        base_url=BASE_URL,
        stream=False
    )

    # 模拟考试设置提取输入
    input = ExamSettingsInput(
        text_content="本次期末考试时间为2024年1月15日 14:00-16:00，考试时长为120分钟。允许提前30分钟入场，开考后15分钟禁止入场。考试剩余30分钟可交卷，及格线为60%。"
    )

    # 运行提取
    output = asyncio.run(agent.extract_settings(input))
    print(json.loads(output.model_dump_json()))