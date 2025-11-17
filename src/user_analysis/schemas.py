from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel


class QuestionType(Enum):
    SINGLE_CHOICE = "单选题"
    MULTIPLE_CHOICE = "多选题"
    TRUE_FALSE = "判断题"
    FILL_IN_BLANK = "填空题"
    SHORT_ANSWER = "简答题"
    PROGRAMMING = "编程题"


class ChartType(Enum):
    BAR_CHART = "柱状图"
    LINE_CHART = "折线图"
    PIE_CHART = "饼图"
    SCATTER_PLOT = "散点图"
    HISTOGRAM = "直方图"
    OTHER = "其他"


class QuestionAnalysis(BaseModel):
    question_number: str
    question_type: QuestionType
    knowledge_point: str
    score: int
    student_score: int
    correct_answer: str
    student_answer: str


class SectionAnalysis(BaseModel):
    section_name: str
    question_type: QuestionType
    total_score: int
    student_score: int
    questions: List[QuestionAnalysis]


class StudentReport(BaseModel):
    sections: List[SectionAnalysis]
    knowledge_mastery: Dict[str, float]
    learning_suggestions: List[str]


class ChartAnalysis(BaseModel):
    chart_type: ChartType
    title: str
    description: str
    data_insights: List[str]
    summary: str


class SectionSummary(BaseModel):
    section_name: str
    question_type: str
    total_score: int
    student_score: int
    percentage: float


class StudentAnalyzeData(BaseModel):
    total_score: int
    student_total_score: int
    sections: List[SectionSummary]
    knowledge_mastery: Dict[str, float]
    learning_suggestions: List[str]
    markdown_report: str
    report_file: str


class StudentAnalyzeResponse(BaseModel):
    success: bool
    message: str
    data: StudentAnalyzeData


class StudentAnalyzeContentRequest(BaseModel):
    content: str


class TeacherAnalyzeData(BaseModel):
    chart_type: str
    title: str
    description: str
    data_insights: List[str]
    summary: str
    teaching_suggestions: List[str]
    markdown_report: str


class TeacherAnalyzeResponse(BaseModel):
    success: bool
    message: str
    data: TeacherAnalyzeData


class TeacherMultipleAnalyzeItem(BaseModel):
    chart_type: str
    title: str
    description: str
    data_insights: List[str]
    summary: str


class TeacherMultipleData(BaseModel):
    chart_count: int
    analyses: List[TeacherMultipleAnalyzeItem]
    comprehensive_suggestions: List[str]
    markdown_report: str


class TeacherMultipleAnalyzeResponse(BaseModel):
    success: bool
    message: str
    data: TeacherMultipleData