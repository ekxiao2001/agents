from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ExamSettingsInput(BaseModel):
    text_content: str = Field(description="包含考试设置信息的文本内容")


class ExamSettingsOutput(BaseModel):
    exam_time: Optional[str] = Field(default=None, description="考试时间（例如：2024年1月15日 14:00-16:00）")
    duration: Optional[str] = Field(default=None, description="考试时长（例如：90分钟）")
    early_entry_time: Optional[str] = Field(default=None, description="提前入场时间（例如：开考前30分钟）")
    late_entry_deadline: Optional[str] = Field(default=None, description="禁止入场时间（例如：开考后15分钟）")
    submission_time_setting: Optional[str] = Field(default=None, description="交卷时间设置（例如：考试剩余30分钟可交卷）")
    passing_score_percentage: Optional[str] = Field(default=None, description="及格线设置（百分比，例如：60%）")

    @field_validator(
        "exam_time",
        "duration",
        "early_entry_time",
        "late_entry_deadline",
        "submission_time_setting",
        "passing_score_percentage",
        mode="before",
    )
    def strip_strings(cls, v):
        """自动去除字符串首尾空白字符"""
        if isinstance(v, str):
            return v.strip()
        return v


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
    "ExamSettingsInput",
    "ExamSettingsOutput",
    "StandardResponse",
]