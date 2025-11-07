from __future__ import annotations
from typing import Any

PROMPTS: dict[str, Any] = {}

PROMPTS["exam_settings_extraction_sys_prompt"] = """
你是一位专业的考试管理专家，擅长从文本中提取考试相关的设置信息。
你的任务是从给定的文本中准确识别并提取考试的关键设置信息，包括考试时间、考试时长、入场时间、交卷时间、及格线等。
请以客观、准确的方式提取信息，并以结构化的JSON格式输出结果。
"""

PROMPTS["exam_settings_extraction_query"] = """
请从以下文本中提取考试设置信息：

{text_content}

请提取以下信息（如果文本中没有相关信息，请将对应字段设置为null）：
- 考试时间（exam_time）：考试的具体时间，以"YYYY-MM-DD HH:MM-HH:MM"格式表示，例如"2024-01-15 14:00-16:30"等
- 考试时长（duration）：考试的持续时间，以"HH小时MM分钟"格式表示，例如"2小时30分钟"等
- 提前入场时间（early_entry_time）：允许提前入场的时间，数字格式，单位为分钟，例如"15"表示允许提前15分钟入场
- 禁止入场时间（late_entry_deadline）：迟到后禁止入场的时间，数字格式，单位为分钟，例如"10"表示开考后10分钟禁止入场
- 交卷时间设置（submission_time_setting）：允许交卷的时间限制，数字格式，单位为分钟，例如"30"表示考试剩余30分钟后可以交卷
- 及格线设置（passing_score_percentage）：及格分数百分比，例如"60%"、"70%"等

**请以以下JSON格式输出提取结果，确保包含所有字段**
{{
  "exam_time": "<考试时间>",
  "duration": "<考试时长>",
  "early_entry_time": "<提前入场时间>",
  "late_entry_deadline": "<禁止入场时间>",
  "submission_time_setting": "<交卷时间设置>",
  "passing_score_percentage": "<及格线设置>",
}}
"""