import sys, asyncio
import re
import glob
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

from agentscope.model import OpenAIChatModel, DashScopeChatModel
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter, DashScopeChatFormatter
from agentscope.message import Msg

from src.user_analysis.prompts import (
    student_sys_prompt,
    extract_knowledge_points_prefix,
    extract_knowledge_points_suffix,
    analyze_mastery_prefix,
    analyze_mastery_suffix,
    learning_suggestions_prefix,
    learning_suggestions_suffix,
)
from src.user_analysis.schemas import (
    QuestionType,
    QuestionAnalysis,
    SectionAnalysis,
    StudentReport,
)


# 加载配置文件
import os
import yaml
conf_path = os.path.join(os.path.dirname(__file__), 'conf.yaml')
with open(conf_path, 'r', encoding='utf-8') as f:
    CONF = yaml.safe_load(f)

LLM_BINDING = CONF.get("LLM_BINDING") or os.getenv("LLM_BINDING") or "deepseek"
MODEL_NAME = CONF.get("MODEL_NAME") or os.getenv("MODEL_NAME") or "deepseek-chat"
API_KEY = CONF.get("API_KEY") or os.getenv("API_KEY") or ""
BASE_URL = CONF.get("BASE_URL") or os.getenv("BASE_URL") or "https://api.deepseek.com"

class StudentAnswerAnalyzer:
    """学生答题卡分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.answer_sheet_content = ""

        if LLM_BINDING == "openai":
            self.formatter = OpenAIChatFormatter()
            self.model = OpenAIChatModel(
                model_name=MODEL_NAME,
                api_key=API_KEY,
                stream=False,
                client_args={"base_url": BASE_URL},
            )
        elif LLM_BINDING == "dashscope":
            self.formatter = DashScopeChatFormatter()
            self.model = DashScopeChatModel(
                model_name=MODEL_NAME,
                api_key=API_KEY,
                stream=False,
            )
    
    def create_agent(self):
        """创建Agent实例"""
        # 创建Agent
        agent = ReActAgent(
            name="StudentAnswerAnalyzer",
            sys_prompt=student_sys_prompt(),
            model=self.model,
            formatter=self.formatter,
        )
        
        return agent
    
    def parse_answer_sheet(self, answer_sheet_content: str) -> StudentReport:
        """解析答题卡文件并生成个性化报告
        
        Args:
            answer_sheet_content: 答题卡文件内容
            
        Returns:
            StudentReport: 学生个性化报告
        """
        # 存储整个答题卡内容到实例变量
        self.answer_sheet_content = answer_sheet_content
        
        # 解析各个题型部分
        sections = self._parse_sections(answer_sheet_content)
        
        # 初始化空的学习建议列表
        learning_suggestions = []
        
        return StudentReport(
            sections=sections,
            knowledge_mastery={}, 
            learning_suggestions=learning_suggestions
        )
    
    def _parse_sections(self, content: str) -> List[SectionAnalysis]:
        """解析各个题型部分"""
        sections = []
        
        # 定义题型模式
        section_patterns = {
            QuestionType.SINGLE_CHOICE: r"## \S+?、.*?单选题.*?## \S+?、",
            QuestionType.MULTIPLE_CHOICE: r"## \S+?、.*?多选题.*?## \S+?、",
            QuestionType.TRUE_FALSE: r"## \S+?、.*?判断题.*?## \S+?、",
            QuestionType.FILL_IN_BLANK: r"## \S+?、.*?填空题.*?## \S+?、",
            QuestionType.SHORT_ANSWER: r"## \S+?、.*?简答题.*?## \S+?、",
            QuestionType.PROGRAMMING: r"## \S+?、.*?编程题.*?## 考试总结|$"
        }

        for question_type, pattern in section_patterns.items():
            section_match = re.search(pattern, content, re.DOTALL)
            if section_match:
                section_content = section_match.group(0)
                section_analysis = self._parse_section(section_content, question_type)
                if section_analysis:
                    sections.append(section_analysis)
        
        return sections
    
    def _parse_section(self, section_content: str, question_type: QuestionType) -> SectionAnalysis:
        """解析单个题型部分"""
        # 提取题型名称
        section_name_match = re.search(r"## \S+?、(.+?)（", section_content)
            
        section_name = section_name_match.group(1) if section_name_match else question_type.value
        
        # 提取总分和学生得分
        score_match = re.search(r"得分：(\d+)", section_content)
        student_score = int(score_match.group(1)) if score_match else 0
        
        total_score_match = re.search(r"共(\d+)分", section_content)
        total_score = int(total_score_match.group(1)) if total_score_match else 0
        
        # 解析题目
        questions = self._parse_questions(section_content, question_type)
        
        return SectionAnalysis(
            section_name=section_name,
            question_type=question_type,
            total_score=total_score,
            student_score=student_score,
            questions=questions
        )
    
    def _parse_questions(self, section_content: str, question_type: QuestionType) -> List[QuestionAnalysis]:
        """解析题目"""
        questions = []
        
        # 使用简单的字符串分割方法提取题目
        if question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, 
                           QuestionType.TRUE_FALSE, QuestionType.FILL_IN_BLANK, 
                           QuestionType.SHORT_ANSWER, QuestionType.PROGRAMMING]:
            # 所有题型都按题目分割
            question_blocks = re.split(r"### 第\d+题", section_content)
            for i, block in enumerate(question_blocks[1:], 1):
                question = self._parse_question(block, question_type, i)
                questions.append(question)
        
        return questions
    
    def _extract_question_content(self, block: str, question_type: QuestionType, index: int) -> str:
        """提取题目内容"""
        lines = block.strip().split('\n')
        if lines:
            question_content = lines[0].strip()
            # 如果第一行是空的，尝试下一行
            if not question_content and len(lines) > 1:
                question_content = lines[1].strip()
        else:
            question_content = f"{question_type.value}{index}"
        
        return question_content
    
    def _extract_scores(self, block: str) -> tuple:
        """提取分数信息"""
        score_match = re.search(r"（(\d+)分）", block)
        score = score_match.group(1) if score_match else "0"
        
        student_score_match = re.search(r"得分：(\d+)", block)
        student_score = student_score_match.group(1) if student_score_match else "0"
        
        return score, student_score
    
    def _extract_answers(self, block: str, is_subjective: bool = False) -> tuple:
        """提取答案信息"""
        if is_subjective:
            # 主观题的答案可能跨越多行
            student_answer_match = re.search(r"\*\*学生答案\*\*：\s*(.+?)(?=\*\*正确答案\*\*|$)", block, re.DOTALL)
            correct_answer_match = re.search(r"\*\*正确答案\*\*：\s*(.+?)(?=\*\*答案解析\*\*|$)", block, re.DOTALL)
        else:
            # 客观题的答案通常在一行内
            student_answer_match = re.search(r"\*\*学生答案\*\*：(.+?)(?=\n|$)", block)
            correct_answer_match = re.search(r"\*\*正确答案\*\*：(.+?)(?=\n|$)", block)
        
        student_answer = student_answer_match.group(1).strip() if student_answer_match else ""
        correct_answer = correct_answer_match.group(1).strip() if correct_answer_match else ""
        
        return student_answer, correct_answer
    
    def _parse_question(self, block: str, question_type: QuestionType, index: int) -> QuestionAnalysis:
        """解析题目"""
        # 提取题目内容
        question_content = self._extract_question_content(block, question_type, index)
        
        # 提取分数信息
        score, student_score = self._extract_scores(block)
        
        # 根据题型确定是否为主观题（答案可能跨越多行）
        is_subjective = question_type in [QuestionType.SHORT_ANSWER, QuestionType.PROGRAMMING]
        
        # 提取学生答案和正确答案
        student_answer, correct_answer = self._extract_answers(block, is_subjective=is_subjective)
        
        # 使用实际的题目内容作为初始知识点
        knowledge_point = question_content if question_content else f"{question_type.value}{index}"
        
        return QuestionAnalysis(
            question_number=str(index),
            question_type=question_type,
            knowledge_point=knowledge_point,
            score=int(score),
            student_score=int(student_score),
            correct_answer=correct_answer,
            student_answer=student_answer
        )
    
    async def _extract_knowledge_points_with_llm(self, sections: List[SectionAnalysis]) -> None:
        """使用大模型从所有题目中提取知识点并存储到内存"""
        # 构建输入给大模型的提示
        prompt = extract_knowledge_points_prefix()
        
        # 收集所有题目
        question_list = []
        
        for section in sections:
            for question in section.questions:
                question_info = {
                    "题号": question.question_number,
                    "题型": question.question_type.value,
                    "题目内容": question.knowledge_point
                }
                question_list.append(question_info)
        
        for q in question_list:
            # 清理题目内容中的特殊字符
            clean_question_content = self._clean_text(q['题目内容'])
            # 清理题型中的特殊字符
            clean_question_type = self._clean_text(q['题型'])
            
            # 构造题目信息
            question_info = f"题号{q['题号']} ({clean_question_type})：{clean_question_content}\n"
            
            prompt += question_info
        
        prompt += extract_knowledge_points_suffix()
        
        # 创建Agent实例
        agent = self.create_agent()
        
        # 发送消息，确保内容中不包含可能导致JSON解析错误的字符
        # 清理特殊字符
        clean_prompt = self._clean_text_for_prompt(prompt)
        msg = Msg(name="user", content=clean_prompt, role="user")
        response = await agent.reply(msg)
        
        # 提取内容
        result = str(response.content) if hasattr(response, 'content') else str(response)
        
        # 解析结果
        lines = result.strip().split('\n')
        knowledge_points = {}
        
        for line in lines:
            if ':' in line:
                try:
                    question_number, knowledge_point = line.split(':', 1)
                    # 清理知识点名称中的特殊字符
                    clean_knowledge_point = self._clean_text(knowledge_point)
                    knowledge_points[question_number.strip()] = clean_knowledge_point
                except ValueError:
                    # 如果解析失败，跳过该行
                    continue
        
        # 更新题目中的知识点
        for section in sections:
            for question in section.questions:
                if question.question_number in knowledge_points:
                    new_knowledge_point = knowledge_points[question.question_number]
                    # 更新问题分析中的知识点
                    question.knowledge_point = new_knowledge_point
    
    async def _analyze_knowledge_mastery_with_llm(self, sections: List[SectionAnalysis]) -> Dict[str, float]:
        """使用大模型分析知识点掌握程度"""
        # 构建输入给大模型的提示
        prompt = analyze_mastery_prefix()
        
        # 收集所有知识点和答题情况
        knowledge_questions = {}
        
        for section in sections:
            for question in section.questions:
                knowledge = question.knowledge_point
                if knowledge not in knowledge_questions:
                    knowledge_questions[knowledge] = []
                
                # 记录题目信息（包含答案内容，用于调试）
                question_info = {
                    "题号": question.question_number,
                    "题型": question.question_type.value,
                    "题目得分": question.student_score,
                    "题目总分": question.score,
                    "正确答案": question.correct_answer,
                    "学生答案": question.student_answer
                }
                knowledge_questions[knowledge].append(question_info)
        
        # 首先基于客观题的答对比例和主观题的得分率计算初步掌握程度
        preliminary_mastery = {}
        for knowledge, questions in knowledge_questions.items():
            objective_questions = [q for q in questions if q['题型'] in ['单选题', '多选题', '判断题', '填空题']]
            subjective_questions = [q for q in questions if q['题型'] in ['简答题', '编程题']]
            
            total_mastery_score = 0
            total_questions = 0
            
            # 处理客观题：基于答对比例
            if objective_questions:
                correct_count = sum(1 for q in objective_questions if q['题目得分'] == q['题目总分'])
                objective_mastery = (correct_count / len(objective_questions)) * 100
                total_mastery_score += objective_mastery * len(objective_questions)
                total_questions += len(objective_questions)
            
            # 处理主观题：基于得分率
            if subjective_questions:
                subjective_score = sum(q['题目得分'] for q in subjective_questions)
                subjective_total = sum(q['题目总分'] for q in subjective_questions)
                if subjective_total > 0:
                    subjective_mastery = (subjective_score / subjective_total) * 100
                else:
                    subjective_mastery = 0
                total_mastery_score += subjective_mastery * len(subjective_questions)
                total_questions += len(subjective_questions)
            
            if total_questions > 0:
                preliminary_mastery[knowledge] = total_mastery_score / total_questions
            else:
                preliminary_mastery[knowledge] = 0.0
        
        for knowledge, questions in knowledge_questions.items():
            # 构造知识点信息
            # 清理知识点名称中的特殊字符
            clean_knowledge = self._clean_text(knowledge)
            knowledge_info = f"知识点：{clean_knowledge}\n"
            
            # 添加初步掌握程度信息
            knowledge_info += f"初步掌握程度：{preliminary_mastery[knowledge]:.1f}%\n"
            
            for q in questions:
                # 清理题型中的特殊字符
                clean_question_type = self._clean_text(q['题型'])
                
                # 区分客观题和主观题
                # 客观题：单选题、多选题、判断题、填空题（只统计对错）
                # 主观题：简答题、编程题（需要看得分率）
                is_objective = q['题型'] in ['单选题', '多选题', '判断题', '填空题']
                
                # 构建题目信息，包含答案内容
                if "正确答案" in q and "学生答案" in q:
                    # 包含答案内容，但需要清理特殊字符
                    clean_correct_answer = self._clean_text(q['正确答案'])
                    clean_student_answer = self._clean_text(q['学生答案'])
                    if is_objective:
                        # 对于客观题，只显示是否正确
                        is_correct = q['题目得分'] == q['题目总分']
                        correctness = "正确" if is_correct else "错误"
                        knowledge_info += f"  题号{q['题号']} ({clean_question_type})：{correctness}\n"
                        knowledge_info += f"    正确答案: {clean_correct_answer}\n"
                        knowledge_info += f"    学生答案: {clean_student_answer}\n"
                    else:
                        # 对于主观题，显示得分情况
                        knowledge_info += f"  题号{q['题号']} ({clean_question_type})：{q['题目得分']}/{q['题目总分']}分\n"
                        knowledge_info += f"    正确答案: {clean_correct_answer}\n"
                        knowledge_info += f"    学生答案: {clean_student_answer}\n"
                else:
                    # 不包含答案内容
                    if is_objective:
                        # 对于客观题，只显示是否正确
                        is_correct = q['题目得分'] == q['题目总分']
                        correctness = "正确" if is_correct else "错误"
                        knowledge_info += f"  题号{q['题号']} ({clean_question_type})：{correctness}\n"
                    else:
                        # 对于主观题，显示得分情况
                        knowledge_info += f"  题号{q['题号']} ({clean_question_type})：{q['题目得分']}/{q['题目总分']}分\n"
            knowledge_info += "\n"
            
            prompt += knowledge_info
        
        prompt += analyze_mastery_suffix()
        
        # 创建Agent实例
        agent = self.create_agent()
        
        # 发送消息，确保内容中不包含可能导致JSON解析错误的字符
        # 进一步清理特殊字符
        clean_prompt = self._clean_text_for_prompt(prompt)
        msg = Msg(name="user", content=clean_prompt, role="user")
        response = await agent.reply(msg)
        
        # 提取内容
        result = str(response.content) if hasattr(response, 'content') else str(response)
        
        # 解析结果
        knowledge_mastery = {}
        lines = result.strip().split('\n')
        
        for line in lines:
            if ':' in line:
                try:
                    knowledge, mastery_str = line.split(':', 1)
                    mastery = float(mastery_str.replace('%', '').strip())
                    knowledge_mastery[knowledge.strip()] = mastery
                except ValueError:
                    # 如果解析失败，跳过该行
                    continue
        
        # 对于未能成功解析的知识点，使用初步计算的掌握程度
        for knowledge in knowledge_questions:
            if knowledge not in knowledge_mastery:
                knowledge_mastery[knowledge] = preliminary_mastery[knowledge]
        
        return knowledge_mastery
    
    async def _generate_learning_suggestions_with_llm(self, report: StudentReport) -> List[str]:
        """使用大模型生成学习建议"""
        # 构建输入给大模型的提示
        prompt = learning_suggestions_prefix()
        
        # 按掌握程度排序，优先关注掌握较差的知识点
        sorted_knowledge = sorted(report.knowledge_mastery.items(), key=lambda x: x[1])
        
        # 限制知识点数量，避免提示过长
        max_knowledge_count = 30  # 减少知识点数量以避免过长
        knowledge_count = 0
        
        for knowledge, mastery in sorted_knowledge:
            if knowledge_count >= max_knowledge_count:
                prompt += "... (更多知识点已省略)\n"
                break
            
            # 清理知识点名称中的特殊字符
            clean_knowledge = self._clean_text(knowledge)
            
            # 动态生成状态描述
            if mastery >= 80:
                status = "掌握良好"
            elif mastery >= 60:
                status = "掌握一般"
            else:
                status = "掌握较差"
            prompt += f"- {clean_knowledge}：{mastery}% ({status})\n"
            knowledge_count += 1
        
        # 添加各题型得分情况
        prompt += "\n各题型得分情况：\n"
        
        for section in report.sections:
            # 区分客观题和主观题的描述
            is_objective = section.question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, 
                                                   QuestionType.TRUE_FALSE, QuestionType.FILL_IN_BLANK]
            
            percentage = round((section.student_score / section.total_score) * 100, 2) if section.total_score > 0 else 0
            # 清理题型名称中的特殊字符
            clean_section_name = self._clean_text(section.section_name)
            
            if is_objective:
                # 对于客观题，显示正确率
                prompt += f"- {clean_section_name}：正确率 {percentage}%\n"
            else:
                # 对于主观题，显示得分率
                prompt += f"- {clean_section_name}：得分率 {percentage}%\n"
        
        prompt += learning_suggestions_suffix()

        # 创建Agent实例
        agent = self.create_agent()
        
        # 发送消息，确保内容中不包含可能导致JSON解析错误的字符
        # 进一步清理特殊字符
        clean_prompt = self._clean_text_for_prompt(prompt)
        msg = Msg(name="user", content=clean_prompt, role="user")
        response = await agent.reply(msg)
        
        # 提取内容
        result = str(response.content) if hasattr(response, 'content') else str(response)
        
        # 检查结果是否有效
        if not result.strip() or "无法" in result or "不能" in result:
            raise ValueError("大模型未能成功生成学习建议，请检查模型配置或提示词")
        
        # 将结果分割成建议列表
        suggestions = [line.strip() for line in result.split('\n') if line.strip()]
        return suggestions[:5]  # 最多返回5条建议

    def _clean_text(self, text: str) -> str:
        """清理文本中的特殊字符"""
        if not isinstance(text, str):
            return str(text)
        return text.replace('"', '').replace("'", '').replace('\n', ' ').replace('\r', ' ').strip()
    
    def _clean_text_for_prompt(self, text: str) -> str:
        """为提示词清理文本，包括额外的转义处理"""
        if not isinstance(text, str):
            return str(text)
        # 限制提示长度
        if len(text) > 8000:
            text = text[:8000] + "... (内容过长已截断)"
        return text.replace('\\', '\\\\').replace('"', '\\"').replace("\n", " ").replace("\r", " ")

    def generate_report_markdown(self, report: StudentReport) -> str:
        """生成Markdown格式的报告"""
        md_content = f"""# 学生个性化学习报告

## 知识点掌握情况总结

"""
        # 计算整体掌握情况
        total_score = sum(section.total_score for section in report.sections)
        student_score = sum(section.student_score for section in report.sections)
        overall_percentage = round((student_score / total_score) * 100, 2) if total_score > 0 else 0
        
        if overall_percentage >= 80:
            overall_status = "良好"
        elif overall_percentage >= 60:
            overall_status = "一般"
        else:
            overall_status = "较差"
        
        md_content += f"整体掌握情况：{overall_percentage}% ({overall_status})\n\n"
        
        # 分别显示客观题知识点和主观题知识点的掌握情况
        objective_mastered = []    # 客观题答对的知识点
        objective_wrong = []       # 客观题答错的知识点
        subjective_mastered = []   # 主观题掌握良好的知识点（≥80%）
        subjective_partial = []    # 主观题部分掌握的知识点（60%-79%）
        subjective_weak = []       # 主观题掌握较差的知识点（<60%）
        
        for knowledge, mastery in report.knowledge_mastery.items():
            # 判断该知识点是否来自客观题还是主观题
            # 这里我们根据掌握程度来判断：整数百分比（0%或100%）为客观题，小数为主观题
            if mastery == 0.0 or mastery == 100.0:
                # 客观题知识点
                if mastery == 100.0:
                    objective_mastered.append(knowledge)
                else:
                    objective_wrong.append(knowledge)
            else:
                # 主观题知识点
                if mastery >= 80:
                    subjective_mastered.append((knowledge, mastery))
                elif mastery >= 60:
                    subjective_partial.append((knowledge, mastery))
                else:
                    subjective_weak.append((knowledge, mastery))
        
        # 显示客观题知识点掌握情况
        if objective_mastered:
            md_content += "客观题答对的知识点：\n"
            for knowledge in objective_mastered:
                md_content += f"- {knowledge}\n"
            md_content += "\n"
        
        if objective_wrong:
            md_content += "客观题答错的知识点：\n"
            for knowledge in objective_wrong:
                md_content += f"- {knowledge}\n"
            md_content += "\n"
        
        # 显示主观题知识点掌握情况
        if subjective_mastered:
            md_content += "主观题掌握良好（得分率 ≥80%）：\n"
            for knowledge, mastery in subjective_mastered:
                md_content += f"- {knowledge} ({mastery}%)\n"
            md_content += "\n"
        
        if subjective_partial:
            md_content += "主观题部分掌握（得分率 60%–79%）：\n"
            for knowledge, mastery in subjective_partial:
                md_content += f"- {knowledge} ({mastery}%)\n"
            md_content += "\n"
        
        if subjective_weak:
            md_content += "主观题掌握较差（得分率 <60%）：\n"
            for knowledge, mastery in subjective_weak:
                md_content += f"- {knowledge} ({mastery}%)\n"
            md_content += "\n"
        
        md_content += "## 学习建议\n\n"
        
        for i, suggestion in enumerate(report.learning_suggestions, 1):
            md_content += f"{i}. {suggestion}\n"
        
        return md_content


async def main():
    """主函数 - 示例用法"""
    # 读取答题卡文件，使用glob查找匹配的文件
    import os
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # 确保使用正确的项目根目录
    if not os.path.exists(project_root):
        project_root = os.getcwd()
    
    answer_sheet_patterns = [
        os.path.join(project_root, "src", "user_analysis", "data", "student_input", "数据分析期末考试答题卡*.md"),
        os.path.join(script_dir, "data", "student_input", "数据分析期末考试答题卡*.md"),
        "数据分析期末考试答题卡*.md"
    ]
    
    answer_sheet_content = None
    found_file = None
    
    for pattern in answer_sheet_patterns:
        matching_files = glob.glob(pattern)
        if matching_files:
            # 选择第一个匹配的文件
            found_file = matching_files[0]
            try:
                with open(found_file, "r", encoding="utf-8") as f:
                    answer_sheet_content = f.read()
                    print(f"成功读取答题卡文件: {found_file}")
                    break
            except FileNotFoundError:
                continue
    
    if answer_sheet_content is None:
        # 列出当前目录下的所有文件供调试
        import os
        print("当前目录文件列表:")
        for root, dirs, files in os.walk("."):
            for file in files:
                if "答题卡" in file:
                    print(f"  找到包含'答题卡'的文件: {os.path.join(root, file)}")
        
        raise FileNotFoundError("无法找到任何答题卡文件")
    
    # 创建分析器并生成报告
    analyzer = StudentAnswerAnalyzer()
    report = analyzer.parse_answer_sheet(answer_sheet_content)
    
    # 使用大模型提取知识点
    await analyzer._extract_knowledge_points_with_llm(report.sections)
    
    # 重新分析知识点掌握情况（因为知识点已更新）
    report.knowledge_mastery = await analyzer._analyze_knowledge_mastery_with_llm(report.sections)
    
    # 使用大模型生成学习建议
    report.learning_suggestions = await analyzer._generate_learning_suggestions_with_llm(report)
    
    # 生成Markdown报告
    markdown_report = analyzer.generate_report_markdown(report)
    
    # 使用项目根目录构建绝对路径
    import os
    output_dir = os.path.join(project_root, "src", "user_analysis", "data", "student_output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 生成带时间戳的文件名
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"学生个性化学习报告_{timestamp}.md"
    output_path = os.path.join(output_dir, filename)
    
    # 保存报告
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    
    print(f"学生个性化学习报告已生成并保存至: {output_path}")
    
    print("学生个性化学习报告已生成！")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())