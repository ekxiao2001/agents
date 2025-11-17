import os
import yaml
from fastapi import APIRouter

from src.ScoreJudgment.score_judgment import build_score_judgment_agent
from src.ScoreJudgment.schemas import (
    GradingCriteriaInput,
    ScoreJudgmentInput,
    ScoreJudgmentOutput,
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

score_agent = build_score_judgment_agent(
    llm_binding=LLM_BINDING if LLM_BINDING in ("openai", "dashscope") else "dashscope",
    model_name=MODEL_NAME,
    api_key=API_KEY,
    base_url=BASE_URL,
    stream=False,
)

router = APIRouter(prefix="/score_judgment", tags=["判题"])


@router.post(
    "/get",
    summary="判分",
    description=(
        "根据评分细则对考生答案进行评分，并返回得分与判分理由。\n"
        "若未提供评分细则，将自动生成评分细则后再判分。"
    ),
    response_model=StandardResponse,
)
async def score_judgment_endpoint(payload: ScoreJudgmentInput):
    try:
        result: ScoreJudgmentOutput = await score_agent.score_judgment(payload)
        return StandardResponse(code=0, message="判分成功", data=result.model_dump())
    except Exception as e:
        return StandardResponse(code=500, message=f"判分失败: {e}", data=None)


@router.post(
    "/grading-criteria",
    summary="评分细则生成",
    description="根据题目、题型、标准答案与满分分值自动生成评分细则。",
    response_model=StandardResponse,
)
async def grading_criteria_endpoint(payload: GradingCriteriaInput):
    try:
        criteria: str = await score_agent.grading_criteria_designer(payload)
        return StandardResponse(code=0, message="评分细则生成成功", data={"grading_criteria": criteria})
    except Exception as e:
        return StandardResponse(code=500, message=f"评分细则生成失败: {e}", data=None)