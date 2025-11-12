from typing import Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator


# ---------- API 请求模型 ----------
class ExamQuestion(BaseModel):
    """考题请求体校验模型（API层）"""
    question: str = Field(..., min_length=5, description="考试题目，至少5个字符")
    answer: str = Field(..., min_length=1, description="考试题目答案")
    question_type: Literal[
        "单选题", "多选题", "填空题", "简答题", "计算题", "编程题",
    ] = Field(..., description="考试题目类型")
    answer_analysis: str = Field(..., min_length=1, description="考试题目答案解析")
    knowledge_point: Optional[str] = Field(
        default="", description="考试题目所属的知识点"
    )
    knowledge_point_description: Optional[str] = Field(
        default="", description="考试题目所属的知识点的具体描述"
    )
    extra_requirement: Optional[str] = Field(
        default="", description="考试题目额外要求"
    )

    @field_validator(
        "question", "answer", "question_type", "answer_analysis", "knowledge_point", "knowledge_point_description", "extra_requirement",
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
                "question": "有一个容量为10的背包，现有4件物品，重量分别为[5, 4, 6, 3]，价值分别为[10, 40, 30, 50]。请问如何选择物品才能使背包内物品的总价值最大？最大价值是______。",
                "answer": "选择第2件物品（重量4，价值40）和第4件物品（重量3，价值50），总重量为7，总价值为90。这是最优解。",
                "question_type": "填空题",
                "answer_analysis": "这是一个典型的01背包问题。我们可以使用动态规划来解决：\n1. 创建dp数组，dp[i][j]表示前i件物品在容量为j时的最大价值\n2. 状态转移方程：dp[i][j] = max(dp[i-1][j], dp[i-1][j-weight[i]] + value[i])\n3. 通过计算可得，当容量为10时，最大价值为90\n4. 回溯可得选择的物品是第2件和第4件",
                "knowledge_point": "动态规划",
                "knowledge_point_description": "01背包问题是动态规划的经典应用，通过状态转移方程求解最优解",
                "extra_requirement": ""
            }
        }
    }


class VerificationResult(BaseModel):
    """验证结果请求模型（API层）"""
    is_compliant: bool = Field(..., description="考试题目是否合规")
    suggestion: Optional[str] = Field(default=None, description="修正意见")


class FixRequest(BaseModel):
    """修复请求模型（API层）"""
    exam_question: ExamQuestion
    verification_result: VerificationResult

    model_config = {
        "json_schema_extra": {
            "example": {
                "exam_question": {
                    "question": "有一个容量为10的背包，现有4件物品，重量分别为[5, 4, 6, 3]，价值分别为[10, 40, 30, 50]。请问如何选择物品才能使背包内物品的总价值最大？最大价值是______。",
                    "answer": "选择第2件物品（重量4，价值40）和第4件物品（重量3，价值50），总重量为7，总价值为90。这是最优解。",
                    "question_type": "填空题",
                    "answer_analysis": "这是一个典型的01背包问题。我们可以使用动态规划来解决：\n1. 创建dp数组，dp[i][j]表示前i件物品在容量为j时的最大价值\n2. 状态转移方程：dp[i][j] = max(dp[i-1][j], dp[i-1][j-weight[i]] + value[i])\n3. 通过计算可得，当容量为10时，最大价值为90\n4. 回溯可得选择的物品是第2件和第4件",
                    "knowledge_point": "动态规划",
                    "knowledge_point_description": "01背包问题是动态规划的经典应用，通过状态转移方程求解最优解",
                    "extra_requirement": ""
                },
                "verification_result": {
                    "is_compliant": False,
                    "suggestion": "**题干**：不符合填空题题型匹配标准。题干描述了一个完整的01背包问题求解过程，要求考生进行物品选择和计算最大价值，这更像是解答题或计算题，而不是填空题。填空题应该只有一个或少量空白处，且有确定唯一答案。\n\n**修改建议**：将题干简化为标准的填空题格式，例如：\"有一个容量为10的背包，现有4件物品，重量分别为[5, 4, 6, 3]，价值分别为[10, 40, 30, 50]。使用动态规划求解，最大价值是______。\"\n\n**答案**：答案格式不符合填空题标准。填空题答案应该是简洁的数值或简短回答，而不是详细的物品选择和解释。\n\n**解析**：解析内容正确，符合动态规划知识点要求，逻辑清晰。",
                },
            }
        }
    }


class VerifyAndFixRequest(BaseModel):
    """验证并修复请求模型（API层）"""
    exam_question: ExamQuestion
    max_fix_attempts: int = Field(
        default=3, ge=1, le=5, description="最大修正次数，范围1-5"
    )


class StandardResponse(BaseModel):
    """标准响应模型（API层）"""
    code: int = Field(..., description="0表示成功，非0表示错误码")
    message: str = Field(..., description="状态说明")
    data: Optional[dict] = Field(default=None, description="返回数据")

    @property
    def is_success(self) -> bool:
        """便捷方法：检查请求是否成功"""
        return self.code == 0


# ---------- 导出列表 ----------
__all__ = [
    # 枚举类型
    "QuestionType",
    # 内部业务模型
    "ExamQuestion",
    "VerificationResult",
    # API 请求模型
    "FixRequest",
    "VerifyAndFixRequest",
]