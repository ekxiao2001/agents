from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Body
import os
import datetime

from src.user_analysis.student_analyzer import StudentAnswerAnalyzer
from src.user_analysis.teacher_analyzer_multimodal import TeacherChartAnalyzer

from src.user_analysis.schemas import (
    StudentAnalyzeResponse,
    StudentAnalyzeContentRequest,
    TeacherAnalyzeResponse,
    TeacherMultipleAnalyzeResponse,
)

router = APIRouter(prefix="/user_analysis", tags=["用户分析"])

student_analyzer = StudentAnswerAnalyzer()
teacher_analyzer = TeacherChartAnalyzer()


# @router.get("/student")
# async def student_root():
#     return {"service": "学生答题分析服务", "description": "基于AgentScope和大模型的学生答题卡分析服务"}


@router.post("/student_analyze_file", response_model=StudentAnalyzeResponse, description="分析学生答题卡")
async def analyze_answer_sheet(file: UploadFile = File(...)) -> StudentAnalyzeResponse:
    try:
        content = await file.read()
        answer_sheet_content = content.decode("utf-8")
        report = student_analyzer.parse_answer_sheet(answer_sheet_content)
        await student_analyzer._extract_knowledge_points_with_llm(report.sections)
        report.knowledge_mastery = await student_analyzer._analyze_knowledge_mastery_with_llm(report.sections)
        report.learning_suggestions = await student_analyzer._generate_learning_suggestions_with_llm(report)
        markdown_report = student_analyzer.generate_report_markdown(report)
        total_score = sum(section.total_score for section in report.sections)
        student_total_score = sum(section.student_score for section in report.sections)
        report_dir = "src/user_analysis/data/student_output"
        os.makedirs(report_dir, exist_ok=True)
        report_filename = f"学生个性化学习报告_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = os.path.join(report_dir, report_filename)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        return {
            "success": True,
            "message": "分析完成",
            "data": {
                "total_score": total_score,
                "student_total_score": student_total_score,
                "sections": [
                    {
                        "section_name": s.section_name,
                        "question_type": s.question_type.value,
                        "total_score": s.total_score,
                        "student_score": s.student_score,
                        "percentage": round((s.student_score / s.total_score) * 100, 2) if s.total_score > 0 else 0,
                    }
                    for s in report.sections
                ],
                "knowledge_mastery": report.knowledge_mastery,
                "learning_suggestions": report.learning_suggestions,
                "markdown_report": markdown_report,
                "report_file": report_path,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析过程中出现错误: {str(e)}")


@router.post("/student_analyze_content", response_model=StudentAnalyzeResponse, description="分析学生答题卡内容")
async def analyze_answer_sheet_content(content: str = Body(..., media_type="text/plain")) -> StudentAnalyzeResponse:
    try:
        report = student_analyzer.parse_answer_sheet(content)
        await student_analyzer._extract_knowledge_points_with_llm(report.sections)
        report.knowledge_mastery = await student_analyzer._analyze_knowledge_mastery_with_llm(report.sections)
        report.learning_suggestions = await student_analyzer._generate_learning_suggestions_with_llm(report)
        markdown_report = student_analyzer.generate_report_markdown(report)
        total_score = sum(section.total_score for section in report.sections)
        student_total_score = sum(section.student_score for section in report.sections)
        report_dir = "src/user_analysis/data/student_output"
        os.makedirs(report_dir, exist_ok=True)
        report_filename = f"学生个性化学习报告_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = os.path.join(report_dir, report_filename)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        return {
            "success": True,
            "message": "分析完成",
            "data": {
                "total_score": total_score,
                "student_total_score": student_total_score,
                "sections": [
                    {
                        "section_name": s.section_name,
                        "question_type": s.question_type.value,
                        "total_score": s.total_score,
                        "student_score": s.student_score,
                        "percentage": round((s.student_score / s.total_score) * 100, 2) if s.total_score > 0 else 0,
                    }
                    for s in report.sections
                ],
                "knowledge_mastery": report.knowledge_mastery,
                "learning_suggestions": report.learning_suggestions,
                "markdown_report": markdown_report,
                "report_file": report_path,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析过程中出现错误: {str(e)}")


# @router.get("/teacher")
# async def teacher_root():
#     return {"service": "教师图表分析服务", "description": "基于AgentScope和多模态大模型的教师图表分析服务"}


@router.post("/teacher_analyze_chart", response_model=TeacherAnalyzeResponse, description="分析教师图表")
async def analyze_chart_image(file: UploadFile = File(...)) -> TeacherAnalyzeResponse:
    try:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        chart_analysis = await teacher_analyzer.analyze_chart_image(temp_file_path)
        teaching_suggestions = await teacher_analyzer._generate_suggestions_with_retry(chart_analysis)
        markdown_report = teacher_analyzer.generate_chart_report_markdown(chart_analysis, teaching_suggestions)
        os.remove(temp_file_path)
        return {
            "success": True,
            "message": "图表分析完成",
            "data": {
                "chart_type": chart_analysis.chart_type.value,
                "title": chart_analysis.title,
                "description": chart_analysis.description,
                "data_insights": chart_analysis.data_insights,
                "summary": chart_analysis.summary,
                "teaching_suggestions": teaching_suggestions,
                "markdown_report": markdown_report,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析过程中出现错误: {str(e)}")


@router.post("/teacher_analyze_multiple_charts", response_model=TeacherMultipleAnalyzeResponse, description="分析多个教师图表")
async def analyze_multiple_charts(files: List[UploadFile] = File(...)) -> TeacherMultipleAnalyzeResponse:
    try:
        all_chart_analyses = []
        temp_file_paths: List[str] = []
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        for file in files:
            if not file.filename:
                continue
            temp_file_path = os.path.join(temp_dir, file.filename)
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            temp_file_paths.append(temp_file_path)
            chart_analysis = await teacher_analyzer.analyze_chart_image(temp_file_path)
            all_chart_analyses.append(chart_analysis)
        comprehensive_suggestions = await teacher_analyzer.generate_comprehensive_teaching_suggestions(all_chart_analyses)
        markdown_report = teacher_analyzer.generate_comprehensive_chart_report_markdown(all_chart_analyses, comprehensive_suggestions)
        for p in temp_file_paths:
            if os.path.exists(p):
                os.remove(p)
        return {
            "success": True,
            "message": "多图表综合分析完成",
            "data": {
                "chart_count": len(all_chart_analyses),
                "analyses": [
                    {
                        "chart_type": a.chart_type.value,
                        "title": a.title,
                        "description": a.description,
                        "data_insights": a.data_insights,
                        "summary": a.summary,
                    }
                    for a in all_chart_analyses
                ],
                "comprehensive_suggestions": comprehensive_suggestions,
                "markdown_report": markdown_report,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析过程中出现错误: {str(e)}")