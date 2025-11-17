"""Prompt templates for user analysis components.

This module centralizes all prompt strings used by the user analysis
services, providing factory functions for clarity and reuse.
"""

from typing import List


# ---- Student analysis prompts ----

def student_sys_prompt() -> str:
    return (
        "你是一个专业的教育数据分析专家，能够从学生的答题卡中提取知识点并生成学习建议。"
    )


def extract_knowledge_points_prefix() -> str:
    return "请从以下题目中提取核心知识点，每个题目提取一个简洁明了的知识点名称：\n\n"


def extract_knowledge_points_suffix() -> str:
    return (
        "\n请为每个题目提取一个核心知识点，要求：\n"
        "1. 知识点名称应简洁明了\n"
        "2. 能准确反映题目的核心考查内容\n"
        "3. 避免过于宽泛或过于具体的描述\n\n"
        "请按照如下格式返回结果，每行一个知识点：\n"
        "题号:知识点名称\n"
        "例如：1:数据可视化\n\n"
        "请直接 output结果，不要添加其他内容。"
    )


def analyze_mastery_prefix() -> str:
    return "请根据以下学生的答题情况，分析各知识点的掌握程度，以百分比形式给出评估结果：\n\n"


def analyze_mastery_suffix() -> str:
    return (
        "请分析以上信息，为每个知识点给出一个掌握程度评分（0-100的数值），评分需要考虑：\n"
        "                1. 客观题的答对比例\n"
        "                2. 主观题的得分率\n"
        "                3. 题目难度和分值\n"
        "                4. 答题的稳定性\n"
        "                5. 知识点重要性\n\n"
        "                请参考提供的初步掌握程度，结合题目具体情况给出更准确的评分。\n\n"
        "                请按照如下格式返回结果，每行一个知识点：\n"
        "                知识点名称:掌握程度百分比\n"
        "                例如：数据可视化:85\n\n"
        "                请直接 output结果，不要添加其他内容。\n"
    )


def learning_suggestions_prefix() -> str:
    return "请根据以下学生的考试情况，生成个性化的学习建议：\n\n知识点掌握情况：\n"


def learning_suggestions_suffix() -> str:
    return (
        "\n请根据以上信息，生成3-5条具体的学习建议，要求：\n"
        "1. 针对掌握较差的知识点给出具体的学习方法\n"
        "2. 针对掌握一般的知识点给出巩固建议\n"
        "3. 对掌握良好的知识点给出进一步提升的建议\n"
        "4. 根据题型表现给出练习建议\n"
        "5. 建议要具体可行，避免空泛的表述\n\n"
        "Please directly output suggest content，每条建议占一行， don't add序号或其他 format.\n"
    )


# ---- Teacher analysis prompts ----

def teacher_multimodal_sys_prompt() -> str:
    return (
        "你是一个专业的数据可视化和教育数据分析专家，能够分析图表图片并提取关键信息。"
    )


def teacher_text_sys_prompt() -> str:
    return (
        "你是一个专业的教育数据分析专家，能够从图表信息中提取洞察并生成教学建议。"
    )


def teacher_chart_analysis_text_prompt() -> str:
    return (
        "请仔细分析这张教育数据图表，特别关注以下教育相关信息：\n\n"
        "1. 图表类型识别（雷达图、柱状图、折线图等）\n"
        "2. 图表标题和主题\n"
        "3. 涉及的知识点或技能领域 \n"
        "4. 各项指标的得分率或掌握程度\n"
        "5. 数据中反映的优势和薄弱环节\n"
        "6. 教学改进的关键点\n\n"
        "请重点提取：\n"
        "- 各知识点的掌握程度（百分比或分数）\n"
        "- 学生群体的整体表现趋势\n"
        "- 需要重点关注的教学薄弱点\n"
        "- 数据中体现的教学规律\n\n"
        "请以结构化的方式输出，确保教育数据的准确性。"
    )


def parse_chart_analysis_prompt(analysis_content: str) -> str:
    return (
        "你是一名教育数据分析师，请从以下图表分析中提取关键的教育相关信息：\n\n"
        f"{analysis_content}\n\n"
        "请重点关注：\n"
        "1. 涉及的教学知识点名称\n"
        "2. 学生的掌握程度数据（百分比、得分率）\n"
        "3. 教学优势和薄弱环节\n"
        "4. 需要改进的教学领域\n\n"
        "请按照以下教育数据分析格式输出：\n"
        "1. 图表类型：[具体图表类型]\n"
        "2. 图表标题：[图表标题，包含教学主题]\n"
        "3. 图表描述：[从教学角度描述图表意义]\n"
        "4. 数据洞察：[每行一个教学相关的数据发现，特别是得分率、掌握程度等]\n"
        "5. 总结：[教学改进的关键点]\n\n"
        "请确保输出内容聚焦于教育数据分析。"
    )


def base_teaching_prompt(insights: str) -> str:
    return (
        "你是一名教育数据分析专家，请基于以下图表分析结果生成一份《教学诊断与针对性教学建议》报告。\n\n"
        "图表信息：\n"
        f"{insights}\n\n"
        "请严格按照以下结构和要求生成报告：\n\n"
        "# 一、总体诊断\n"
        "- 从图表中识别学生的知识掌握情况（优势知识点、薄弱环节）\n"
        "- 分析各知识点的得分率分布\n"
        "- 指出教学中的重点和难点\n\n"
        "# 二、针对性教学建议\n"
        "针对识别出的教学问题，提出具体可操作的教学策略：\n"
        "1. 对于薄弱知识点（得分率低）：\n"
        "   - 具体的补救教学方案\n"
        "   - 课时安排建议\n"
        "   - 教学活动设计\n\n"
        "2. 对于中等掌握知识点：\n"
        "   - 巩固强化措施\n"
        "   - 概念澄清方法\n"
        "   - 实践应用训练\n\n"
        "3. 教学实施建议：\n"
        "   - 课堂活动设计\n"
        "   - 作业布置建议\n"
        "   - 评价反馈机制\n\n"
        "要求：\n"
        "- 基于数据说话，引用具体的得分率\n"
        "- 建议要具体可操作，避免空泛\n"
        "- 体现教育心理学和教学法原理\n"
        "- 语言简洁专业，重点突出\n"
        "- 总字数控制在400-600字\n"
    )
