from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
import os
import json
import datetime

from src.exam_generation.multi_type_paper_generator import MultiTypePaperGenerator
from src.exam_generation.knowledge_question_generator import KnowledgeBasedQuestionGenerator
from src.exam_generation.schemas import (
    QuestionTypeConfig,
    GeneratePaperRequest,
    QuestionGenerateRequest,
    GenerateResponse,
)

router = APIRouter(prefix="/exam_generation", tags=["生成考题"])
# router = APIRouter(tags=["生成考题"])

paper_generator = MultiTypePaperGenerator()
question_generator = KnowledgeBasedQuestionGenerator()


# @router.get("/paper")
# async def paper_root() -> Dict[str, str]:
#     return {"service": "试卷生成服务", "description": "基于AgentScope的多题型试卷生成服务"}


@router.post("/paper_generate", response_model=GenerateResponse, description="生成多题型试卷")
async def generate_paper(request: GeneratePaperRequest) -> GenerateResponse:
    try:
        question_types = [
            {"index": qt.index, "type": qt.type, "count": qt.count, "score": qt.score}
            for qt in request.question_types
        ]
        await paper_generator.cache_user_input(request.topic, question_types)
        paper_content, answer_content = await paper_generator.generate_full_paper(
            request.topic, question_types
        )
        if paper_content.startswith("试卷生成失败:"):
            return GenerateResponse(success=False, message=paper_content, data=None)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        paper_filename = f"试卷_{request.topic}_{timestamp}.md"
        answer_filename = f"试卷答案_{request.topic}_{timestamp}.md"
        os.makedirs("generated_papers", exist_ok=True)
        paper_file_path = os.path.join("generated_papers", paper_filename)
        answer_file_path = os.path.join("generated_papers", answer_filename)
        with open(paper_file_path, "w", encoding="utf-8") as f:
            f.write(paper_content)
        with open(answer_file_path, "w", encoding="utf-8") as f:
            f.write(answer_content)
        return GenerateResponse(
            success=True,
            message="试卷生成成功",
            data={"paper_content": paper_content, "answer_content": answer_content},
            file_paths={"paper_file": paper_file_path, "answer_file": answer_file_path},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"试卷生成过程中出现错误: {str(e)}")


@router.get("/paper_get_cached_input/{topic}", description="获取缓存的试卷生成输入")
async def get_cached_input(topic: str) -> Dict[str, Any]:
    try:
        cached_data = await paper_generator.get_cached_input(topic)
        if cached_data:
            return {"success": True, "message": "找到缓存数据", "data": cached_data}
        else:
            return {"success": False, "message": "未找到缓存数据", "data": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存数据时出现错误: {str(e)}")


# @router.get("/question")
# async def question_root() -> Dict[str, str]:
#     return {"service": "考题生成服务", "description": "基于知识点的考题生成服务"}


@router.post("/question_generate", response_model=Dict[str, Any], description="生成考题")
async def generate_questions(request: QuestionGenerateRequest) -> Dict[str, Any]:
    try:
        if request.description and request.description.strip():
            result = await question_generator.generate_questions(description=request.description)
        elif (
            request.topic
            and request.topic.strip()
            and request.knowledge_points
            and len(request.knowledge_points) > 0
            and request.question_type
            and request.question_type.strip()
            and request.count is not None
            and request.count > 0
        ):
            description = (
                f"请为《{request.topic}》课程生成{request.count}道{request.question_type}，"
                f"难度为{request.difficulty}，基于以下知识点：{', '.join(request.knowledge_points)}"
            )
            result = await question_generator.generate_questions(
                request.topic,
                request.knowledge_points,
                request.question_type,
                request.count,
                description,
            )
        else:
            return {"success": False, "message": "考题生成失败: 缺少必要的参数信息", "data": None}
        if result.startswith("考题生成失败:"):
            return {"success": False, "message": result, "data": None}
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if request.description and request.description.strip():
            filename = f"考题_需求描述_{timestamp}.json"
        else:
            filename = f"考题_{request.topic}_{request.question_type}_{timestamp}.json"
        os.makedirs("generated_questions", exist_ok=True)
        file_path = os.path.join("generated_questions", filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(result)
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError:
            result_data = {"raw_content": result}
        return {"success": True, "message": "考题生成成功", "data": result_data, "file_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成考题时发生错误: {str(e)}")