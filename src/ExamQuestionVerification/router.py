import os
import yaml
from fastapi import APIRouter

from src.ExamQuestionVerification.exam_question_verification import build_exam_verifier
from src.ExamQuestionVerification.schemas import (
    ExamQuestion,
    VerificationResult,
    FixRequest,
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

verifier = build_exam_verifier(
    llm_binding=LLM_BINDING if LLM_BINDING in ("openai", "dashscope") else "dashscope",
    model_name=MODEL_NAME,
    api_key=API_KEY,
    base_url=BASE_URL,
    stream=False,
)

router = APIRouter(prefix="/verification", tags=["考题检修"])


@router.post(
    "/eqv",
    summary="考题核查",
    description="根据考题信息判断是否合规，并返回修正建议。",
    response_model=StandardResponse,
)
async def verify_endpoint(payload: ExamQuestion):
    try:
        res: VerificationResult = await verifier.verify_exam_question(payload)
        return StandardResponse(code=0, message="考题核查成功", data=res.model_dump())
    except Exception as e:
        return StandardResponse(code=500, message=f"核查失败: {e}", data=None)


@router.post(
    "/eqf",
    summary="考题修复",
    description="基于核查结果修复考题，返回修复后的考题信息。",
    response_model=StandardResponse,
)
async def fix_endpoint(payload: FixRequest):
    try:
        eq = ExamQuestion(**payload.exam_question.model_dump())
        ver = VerificationResult(**payload.verification_result.model_dump())
        new_eq: ExamQuestion = await verifier.fix_exam_question(eq, ver)
        return StandardResponse(code=0, message="考题修复成功", data=new_eq.model_dump())
    except Exception as e:
        return StandardResponse(code=500, message=f"修复失败: {e}", data=None)