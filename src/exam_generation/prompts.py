"""Prompt templates for exam generation components.

This module centralizes all prompt strings used by the exam generation
services, providing typed factory functions for clarity and reuse.
"""

from typing import List


def multi_type_sys_prompt() -> str:
    """System prompt for multi-type paper generation agent."""
    return (
        "你是一位专业的课程试卷生成专家。\n"
        "你的任务是根据课程名称和多种题型要求生成完整的大学试卷。\n"
        "请严格按照要求生成内容，确保试卷结构完整、题目合理、答案准确。"
    )


def paper_generation_prompt(topic: str, type_descriptions: List[str], total_score: int) -> str:
    """Build the prompt for generating a complete paper.

    Args:
        topic: Course name.
        type_descriptions: Section descriptions (index, type, count, score aggregation).
        total_score: Total score of the paper.

    Returns:
        Prompt string.
    """
    sections = "   ".join(type_descriptions)
    return (
        f"请为《{topic}》课程生成一套完整的试卷：\n\n"
        "要求：\n"
        f"1. 试卷标题：{topic}期末试卷\n"
        "2. 考试时间：120分钟\n"
        f"3. 总分：{total_score}分\n"
        "4. 题型包括：\n"
        f"   {sections}\n"
        f"5. 题目必须符合大学中{topic}课程的内容和难度\n"
        "6. 使用Markdown格式\n"
        "7. 试卷结构完整，包含试卷头部、各题型题目和必要的说明\n\n"
        "请生成完整的试卷。"
    )


def answers_generation_prompt(paper_content: str) -> str:
    """Build the prompt for generating answers and analysis.

    Args:
        paper_content: Previously generated paper content in Markdown.

    Returns:
        Prompt string.
    """
    return (
        "请为以下试卷生成详细的答案和解析：\n\n"
        "试卷内容：\n"
        f"{paper_content}\n\n"
        "要求：\n"
        "1. 严格按照试卷中的题目顺序进行解答\n"
        "2. 每道题都要给出标准答案\n"
        "3. 对于主观题，需要给出评分要点和参考答案\n"
        "4. 答案要准确、简洁，解析要详细、易懂\n"
        "5. 题型分类清晰，格式规范\n"
        "6. 使用Markdown格式\n\n"
        "请生成详细的答案和解析。"
    )


def knowledge_sys_prompt() -> str:
    """System prompt for knowledge-based question generation agent."""
    return (
        "你是一位专业的课程考题生成专家。\n"
        "你的任务是根据课程名称和知识点生成相关的考题，或者根据用户提供的需求描述生成考题。\n"
        "请严格按照要求生成内容，确保考题与知识点或需求描述紧密相关、难度适中、答案准确。"
    )


def questions_by_knowledge_prompt(
    topic: str, knowledge_points: List[str], question_type: str, count: int
) -> str:
    """Build prompt for generating questions by knowledge points."""
    knowledge_str = "\n".join([f"{i+1}. {kp}" for i, kp in enumerate(knowledge_points)])
    return (
        f"请为《{topic}》课程生成{count}道{question_type}，基于以下知识点：\n\n"
        f"知识点：\n{knowledge_str}\n\n"
        "要求：\n"
        f"1. 考题标题：{topic} {question_type}\n"
        f"2. 题目数量：{count}道\n"
        "3. 题目必须紧密围绕提供的知识点\n"
        "4. 每个题目必须对应详细的解析，解析要符合大学课程水平\n"
        "5. 难度适中，符合大学课程水平\n"
        "6. 生成json格式，包含以下字段：\n"
        "- question: 考试题目\n"
        "- answer: 考试题目答案\n"
        "- question_type: 考试题目类型\n"
        "- knowledge_point: 考试题目所属的知识点\n"
        "- knowledge_point_description: 考试题目所属的知识点的具体描述\n"
        "- knowledge_Analysis: 考试题目的答案解析\n"
        "- extra_requirement: 考试题目额外要求\n\n"
        "例如:\n"
        "{\n"
        "  \"question\": \"示例题目\",\n"
        "  \"answer\": \"B\",\n"
        "  \"question_type\": \"选择题\",\n"
        "  \"knowledge_point\": \"示例知识点\",\n"
        "  \"knowledge_point_description\": \"知识点描述\",\n"
        "  \"knowledge_Analysis\": \"解析\",\n"
        "  \"extra_requirement\": \"\"\n"
        "}\n\n"
        "请生成考题。"
    )


def questions_by_description_prompt(description: str) -> str:
    """Build prompt for generating questions by free-form description."""
    return (
        "请根据以下需求描述生成相关的考题：\n\n"
        "需求描述：\n"
        f"{description}\n\n"
        "要求：\n"
        "1. 仔细分析需求描述中的课程、知识点、题型和数量等信息\n"
        "2. 生成的考题必须紧密围绕需求描述的内容\n"
        "3. 每个题目必须对应详细的解析，解析要符合大学课程水平\n"
        "4. 难度适中，符合大学课程水平\n"
        "5. 生成json格式，包含以下字段：\n"
        "- question\n- answer\n- question_type\n- knowledge_point\n"
        "- knowledge_point_description\n- knowledge_Analysis\n- extra_requirement\n\n"
        "例如:\n"
        "{\n"
        "  \"question\": \"示例题目\",\n"
        "  \"answer\": \"B\",\n"
        "  \"question_type\": \"选择题\",\n"
        "  \"knowledge_point\": \"示例知识点\",\n"
        "  \"knowledge_point_description\": \"知识点描述\",\n"
        "  \"knowledge_Analysis\": \"解析\",\n"
        "  \"extra_requirement\": \"\"\n"
        "}\n\n"
        "请生成考题。"
    )


def questions_combined_prompt(
    topic: str,
    knowledge_points: List[str],
    question_type: str,
    count: int,
    description: str,
) -> str:
    """Build prompt combining structured input and user description."""
    knowledge_str = "\n".join([f"{i+1}. {kp}" for i, kp in enumerate(knowledge_points)])
    return (
        "你是一位专业的课程考题生成专家。请根据以下信息生成相关的考题：\n\n"
        "结构化输入信息：\n"
        f"- 课程名称：{topic or '未提供'}\n"
        f"- 知识点：\n{knowledge_str or '未提供'}\n"
        f"- 题型：{question_type or '未提供'}\n"
        f"- 题目数量：{count if count > 0 else '未提供'}\n\n"
        "用户自定义需求描述：\n"
        f"{description or '未提供'}\n\n"
        "要求：\n"
        "1. 请综合分析以上所有信息\n"
        "2. 当结构化输入信息与用户自定义需求描述存在冲突时，以用户自定义需求描述为准\n"
        "3. 如果用户自定义需求描述中没有明确提到某些信息（如课程名称、知识点、题型、数量等），请使用结构化输入中的对应信息\n"
        "4. 生成的考题必须紧密围绕最终确定的内容\n"
        "5. 每个题目必须对应详细的解析，解析要符合大学课程水平\n"
        "6. 难度适中，符合大学课程水平\n"
        "7. 生成json格式，只包含以下字段：\n"
        "- question\n- answer\n- question_type\n- knowledge_point\n"
        "- knowledge_point_description\n- knowledge_Analysis\n- extra_requirement\n\n"
        "例如:\n"
        "{\n"
        "  \"question\": \"示例题目\",\n"
        "  \"answer\": \"B\",\n"
        "  \"question_type\": \"选择题\",\n"
        "  \"knowledge_point\": \"示例知识点\",\n"
        "  \"knowledge_point_description\": \"知识点描述\",\n"
        "  \"knowledge_Analysis\": \"解析\",\n"
        "  \"extra_requirement\": \"\"\n"
        "}"
    )