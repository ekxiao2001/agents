from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QuestionTypeConfig(BaseModel):
    index: str = Field(..., description="题型序号或名称")
    type: str = Field(..., description="题型名称，如：选择题、简答题等")
    count: int = Field(..., ge=1, description="题目数量（>=1）")
    score: int = Field(..., ge=1, description="每题分值（>=1）")


class GeneratePaperRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="课程名称")
    question_types: List[QuestionTypeConfig] = Field(default_factory=list, description="题型配置列表")


class QuestionGenerateRequest(BaseModel):
    topic: Optional[str] = Field(default="", description="课程名称，可选")
    knowledge_points: Optional[List[str]] = Field(default_factory=list, description="知识点列表")
    question_type: Optional[str] = Field(default="", description="题型名称，可选")
    count: Optional[int] = Field(default=0, ge=0, description="题目数量，0 表示未提供")
    difficulty: Optional[str] = Field(default="一般", description="难度等级")
    description: Optional[str] = Field(default="", description="自由描述，与结构化输入合并使用")


class GenerateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    file_paths: Optional[Dict[str, str]] = None