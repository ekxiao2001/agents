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
        "智慧教育智能体 API，提供生成考题、考题检修、判题、考试设置及用户分析等功能。"
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "生成考题"},
        {"name": "考题检修"},
        {"name": "判题"},
        {"name": "考试设置"},
        {"name": "用户分析"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from src.exam_generation.router import router as exam_router
from src.ExamQuestionVerification.router import router as verification_router
from src.ScoreJudgment.router import router as judgment_router
from src.ExamSettingsExtraction.router import router as settings_router
from src.user_analysis.router import router as analysis_router

app.include_router(exam_router)
app.include_router(verification_router)
app.include_router(judgment_router)
app.include_router(settings_router)
app.include_router(analysis_router)


if __name__ == "__main__":
    host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port = int(os.getenv("FASTAPI_PORT", "8000"))

    uvicorn.run(
        "fastapi_server_start:app",
        host=host,
        port=port,
        reload=True,
    )