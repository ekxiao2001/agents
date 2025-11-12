import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# 加载根目录下 .env
ROOT_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(ROOT_DIR, ".env"))


# 统一应用
app = FastAPI(
    title="Agents API",
    description=(
        "统一的考试核查与分数判别服务。提供核查、修复，以及判分与评分细则生成端点。"
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "考题检修"},
        {"name": "判题"},
        {"name": "考试设置"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 初始化功能类 ----------
LLM_BINDING = os.getenv("LLM_BINDING", "deepseek")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
API_KEY = os.getenv("API_KEY", "")
BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")

from src.ExamQuestionVerification.exam_question_verification import build_exam_verifier
from src.ScoreJudgment.score_judgment import build_score_judgment_agent
from src.ExamSettingsExtraction.exam_settings_extraction import (
    build_exam_settings_agent,
)

verifier = build_exam_verifier(
    llm_binding=LLM_BINDING if LLM_BINDING in ("deepseek", "dashscope") else "deepseek",
    model_name=MODEL_NAME,
    api_key=API_KEY,
    base_url=BASE_URL,
    stream=False,
)
score_agent = build_score_judgment_agent(
    llm_binding=LLM_BINDING if LLM_BINDING in ("deepseek", "dashscope") else "deepseek",
    model_name=MODEL_NAME,
    api_key=API_KEY,
    base_url=BASE_URL,
    stream=False,
)
exam_settings_agent = build_exam_settings_agent(
    llm_binding=LLM_BINDING if LLM_BINDING in ("deepseek", "dashscope") else "deepseek",
    model_name=MODEL_NAME,
    api_key=API_KEY,
    base_url=BASE_URL,
    stream=False,
)


# ---------- 健康检查 ----------
@app.get("/", summary="欢迎页")
async def root():
    return JSONResponse(
        status_code=200,
        content={
            "message": "Unified Agents API 服务运行中。访问 /docs 查看交互文档。",
            "data": None,
        },
    )


@app.get("/health", summary="健康检查")
async def health():
    return JSONResponse(
        status_code=200,
        content={
            "message": "ok",
            "data": {"status": "healthy"},
        },
    )


# ---------- 考试核查端点 ----------
from src.ExamQuestionVerification.schemas import (
    ExamQuestion,
    VerificationResult,
    FixRequest,
    StandardResponse,
)


@app.post(
    "/eqv",
    summary="考题核查",
    description="根据考题信息判断是否合规，并返回修正建议。",
    response_model=StandardResponse,
    tags=["考题检修"],
)
async def verify_endpoint(payload: ExamQuestion):
    try:
        res: VerificationResult = await verifier.verify_exam_question(payload)
        return StandardResponse(code=0, message="考题核查成功", data=res.model_dump())
    except Exception as e:
        return StandardResponse(
            code=500,
            message=f"核查失败: {e}",
            data=None,
        )


@app.post(
    "/eqf",
    summary="考题修复",
    description="基于核查结果修复考题，返回修复后的考题信息。",
    response_model=StandardResponse,
    tags=["考题检修"],
)
async def fix_endpoint(payload: FixRequest):
    try:
        eq = ExamQuestion(**payload.exam_question.model_dump())
        ver = VerificationResult(**payload.verification_result.model_dump())
        new_eq: ExamQuestion = await verifier.fix_exam_question(eq, ver)
        return StandardResponse(
            code=0, message="考题修复成功", data=new_eq.model_dump()
        )
    except Exception as e:
        return StandardResponse(
            code=500,
            message=f"修复失败: {e}",
            data=None,
        )


# ---------- 分数判别端点 ----------
from src.ScoreJudgment.schemas import (
    GradingCriteriaInput,
    ScoreJudgmentInput,
    ScoreJudgmentOutput,
    StandardResponse,
)


@app.post(
    "/score-judgment",
    summary="判分",
    description=(
        "根据评分细则对考生答案进行评分，并返回得分与判分理由。\n"
        "若未提供评分细则，将自动生成评分细则后再判分。"
    ),
    response_model=StandardResponse,
    tags=["判题"],
)
async def score_judgment_endpoint(payload: ScoreJudgmentInput):
    try:
        result: ScoreJudgmentOutput = await score_agent.score_judgment(payload)
        return StandardResponse(code=0, message="判分成功", data=result.model_dump())
    except Exception as e:
        return StandardResponse(
            code=500,
            message=f"判分失败: {e}",
            data=None,
        )


@app.post(
    "/grading-criteria",
    summary="评分细则生成",
    description="根据题目、题型、标准答案与满分分值自动生成评分细则。",
    response_model=StandardResponse,
    tags=["判题"],
)
async def grading_criteria_endpoint(payload: GradingCriteriaInput):
    try:
        criteria: str = await score_agent.grading_criteria_designer(payload)
        return StandardResponse(
            code=0, message="评分细则生成成功", data={"grading_criteria": criteria}
        )
    except Exception as e:
        return StandardResponse(
            code=500,
            message=f"评分细则生成失败: {e}",
            data=None,
        )


# ---------- 考试设置提取端点 ----------
from src.ExamSettingsExtraction.schemas import (
    ExamSettingsInput,
    ExamSettingsOutput,
    StandardResponse,
)


@app.post(
    "/exam-settings",
    summary="考试设置提取",
    description="从文本中提取考试设置信息，包括考试时长、考试类型等。",
    response_model=StandardResponse,
    tags=["考试设置"],
)
async def exam_settings_endpoint(payload: ExamSettingsInput):
    try:
        result: ExamSettingsOutput = await exam_settings_agent.extract_settings(payload)
        return StandardResponse(code=0, message="考试设置提取成功", data=result.model_dump())
    except Exception as e:
        return StandardResponse(
            code=500,
            message=f"考试设置提取失败: {e}",
            data=None,
        )


if __name__ == "__main__":
    host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port = int(os.getenv("FASTAPI_PORT", "8000"))

    uvicorn.run(
        "fastapi_server_start:app",
        host=host,
        port=port,
        reload=True,
    )