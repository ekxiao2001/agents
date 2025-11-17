import os
import yaml
from fastapi import APIRouter

from src.ExamSettingsExtraction.exam_settings_extraction import build_exam_settings_agent
from src.ExamSettingsExtraction.schemas import (
    ExamSettingsInput,
    ExamSettingsOutput,
    StandardResponse,
)


# 加载配置文件
import os
conf_path = os.path.join(os.path.dirname(__file__), 'conf.yaml')
with open(conf_path, 'r', encoding='utf-8') as f:
    CONF = yaml.safe_load(f)

LLM_BINDING = os.getenv("LLM_BINDING") or CONF.get("LLM_BINDING") or "dashscope"
MODEL_NAME = os.getenv("MODEL_NAME") or CONF.get("MODEL_NAME") or "qwen-plus"
API_KEY = os.getenv("API_KEY") or CONF.get("API_KEY") or ""
BASE_URL = os.getenv("BASE_URL") or CONF.get("BASE_URL") or "https://api.dashscope.aliyuncs.com"

exam_settings_agent = build_exam_settings_agent(
    llm_binding=LLM_BINDING if LLM_BINDING in ("openai", "dashscope") else "dashscope",
    model_name=MODEL_NAME,
    api_key=API_KEY,
    base_url=BASE_URL,
    stream=False,
)

router = APIRouter(prefix="/exam_settings", tags=["考试设置"])


@router.post(
    "/get",
    summary="考试设置提取",
    description="从文本中提取考试设置信息，包括考试时长、考试类型等。",
    response_model=StandardResponse,
)
async def exam_settings_endpoint(payload: ExamSettingsInput):
    try:
        result: ExamSettingsOutput = await exam_settings_agent.extract_settings(payload)
        return StandardResponse(code=0, message="考试设置提取成功", data=result.model_dump())
    except Exception as e:
        return StandardResponse(code=500, message=f"考试设置提取失败: {e}", data=None)