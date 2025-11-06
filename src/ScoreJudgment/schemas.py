from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

class ScoreJudgmentInput(BaseModel):
    question_title: str = Field(description="考试题目")
    question_type: Literal["填空题", "简答题", "编程题"] = Field(description="考题类型")
    standard_answer: str = Field(description="题目标准答案")
    student_answer: str = Field(description="考生答案")
    full_score: int = Field(description="考题满分分数")
    grading_criteria: Optional[str] = Field(default=None, description="评分细则（可选）")

    @field_validator("full_score", mode="before")
    def full_score_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("考题满分分数必须大于0")
        return v
    
    @field_validator(
        "question_title",
        "question_type",
        "standard_answer",
        "student_answer",
        "grading_criteria",
        mode="before",
    )
    def strip_strings(cls, v):
        """自动去除字符串首尾空白字符"""
        if isinstance(v, str):
            return v.strip()
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question_title": "请编写一个递归函数fibonacci(n)，计算斐波那契数列的第n项。斐波那契数列定义如下：\n- fibonacci(0) = 0\n- fibonacci(1) = 1\n- fibonacci(n) = fibonacci(n-1) + fibonacci(n-2) (n ≥ 2)\n\n要求：\n1. 使用递归方法实现\n2. 函数参数为整数n，返回第n项的值\n3. 处理边界情况（n < 0时返回-1）",
                "question_type": "编程题",
                "standard_answer": "def fibonacci(n):\n    if n < 0:\n        return -1\n    elif n == 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)",
                "student_answer": "def fibonacci(n):\n    if n == 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)",
                "full_score": 10,
                "grading_criteria": "评分细则：\n1. 函数定义正确（2分）：函数名、参数正确\n2. 递归逻辑正确（4分）：正确实现fibonacci(n) = fibonacci(n-1) + fibonacci(n-2)\n3. 边界条件处理（3分）：\n   - 正确处理n=0的情况（1分）\n   - 正确处理n=1的情况（1分）\n   - 正确处理n<0的情况（1分）\n4. 代码规范（1分）：缩进、命名规范等\n\n扣分标准：\n- 缺少边界条件处理n<0扣1分\n- 递归逻辑错误扣4分\n- 函数名或参数错误扣2分",
            }
        }
    }


class GradingCriteriaInput(BaseModel):
    question_title: str = Field(description="考试题目")
    question_type: Literal["填空题", "简答题", "编程题"] = Field(description="考题类型")
    standard_answer: str = Field(description="题目标准答案")
    full_score: int = Field(description="考题满分分数")

    @field_validator("full_score", mode="before")
    def full_score_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("考题满分分数必须大于0")
        return v
    
    @field_validator(
        "question_title",
        "question_type",
        "standard_answer",
        mode="before",
    )
    def strip_strings(cls, v):
        """自动去除字符串首尾空白字符"""
        if isinstance(v, str):
            return v.strip()
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question_title": "请编写一个递归函数fibonacci(n)，计算斐波那契数列的第n项。斐波那契数列定义如下：\n- fibonacci(0) = 0\n- fibonacci(1) = 1\n- fibonacci(n) = fibonacci(n-1) + fibonacci(n-2) (n ≥ 2)\n\n要求：\n1. 使用递归方法实现\n2. 函数参数为整数n，返回第n项的值\n3. 处理边界情况（n < 0时返回-1）",
                "question_type": "编程题",
                "standard_answer": "def fibonacci(n):\n    if n < 0:\n        return -1\n    elif n == 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)",
                "full_score": 10,
            }
        }
    }


class ScoreJudgmentOutput(BaseModel):
    score: int = Field(description="考生得分")
    sj_reason: str = Field(description="判分理由")


class StandardResponse(BaseModel):
    """标准响应模型（API层）"""
    code: int = Field(..., description="0表示成功，非0表示错误码")
    message: str = Field(..., description="状态说明")
    data: Optional[dict] = Field(default=None, description="返回数据")

    @property
    def is_success(self) -> bool:
        """便捷方法：检查请求是否成功"""
        return self.code == 0

__all__ = [
    "ScoreJudgmentInput",
    "ScoreJudgmentOutput",
    "StandardResponse",
]