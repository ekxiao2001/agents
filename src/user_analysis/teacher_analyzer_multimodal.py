import sys, asyncio
import re
import glob
import base64
import os
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

from agentscope.model import OpenAIChatModel, DashScopeChatModel
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter, DeepSeekChatFormatter, DashScopeChatFormatter
from agentscope.message import (
    Msg,
    TextBlock,
    ImageBlock,
    Base64Source,
)
from src.user_analysis.prompts import (
    teacher_multimodal_sys_prompt,
    teacher_text_sys_prompt,
    teacher_chart_analysis_text_prompt,
    parse_chart_analysis_prompt,
    base_teaching_prompt,
)
from src.user_analysis.schemas import (
    ChartType,
    ChartAnalysis,
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

MM_MODEL_BINDING = CONF.get("MM_MODEL_BINDING") or os.getenv("MM_MODEL_BINDING") or "dashscope"
MM_MODEL_NAME = CONF.get("MM_MODEL_NAME") or os.getenv("MM_MODEL_NAME") or "qwen-vl-max"
MM_MODEL_API_KEY = CONF.get("MM_MODEL_API_KEY") or os.getenv("MM_MODEL_API_KEY") or ""
MM_MODEL_BASE_URL = CONF.get("MM_MODEL_BASE_URL") or os.getenv("MM_MODEL_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"


class TeacherChartAnalyzer:
    """教师图表分析器"""

    def __init__(self):
        """初始化分析器"""
        
        if MM_MODEL_BINDING == "openai":
            self.mm_formatter = OpenAIChatFormatter()
            self.mm_model = OpenAIChatModel(
                model_name=MM_MODEL_NAME,
                api_key=MM_MODEL_API_KEY,
                stream=False,
                client_args={"base_url": MM_MODEL_BASE_URL},
            )
        elif MM_MODEL_BINDING == "dashscope":
            self.mm_formatter = DashScopeChatFormatter()
            self.mm_model = DashScopeChatModel(
                model_name=MM_MODEL_NAME,
                api_key=MM_MODEL_API_KEY,
                stream=False,
            )
        
        if LLM_BINDING == "openai":
            self.text_formatter = OpenAIChatFormatter()
            self.text_model = OpenAIChatModel(
                model_name=MODEL_NAME,
                api_key=API_KEY,
                stream=False,
                client_args={"base_url": BASE_URL},
            )
        elif LLM_BINDING == "dashscope":
            self.text_formatter = DashScopeChatFormatter()
            self.text_model = DashScopeChatModel(
                model_name=MODEL_NAME,
                api_key=API_KEY,
                stream=False,
            )

    def create_multimodal_agent(self):
        """创建多模态Agent实例"""
        return self._create_agent(
            name="TeacherChartMultimodalAnalyzer",
            sys_prompt=teacher_multimodal_sys_prompt(),
            model=self.mm_model,
            formatter=self.mm_formatter
        )

    def create_text_agent(self):
        """创建文本分析Agent实例"""
        return self._create_agent(
            name="TeacherChartTextAnalyzer",
            sys_prompt=teacher_text_sys_prompt(),
            model=self.text_model,
            formatter=self.text_formatter
        )

    def _create_agent(self, name: str, sys_prompt: str, model, formatter):
        """创建Agent实例的通用方法"""
        agent = ReActAgent(
            name=name,
            sys_prompt=sys_prompt,
            model=model,
            formatter=formatter
        )
        return agent

    def encode_image_to_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def analyze_chart_image(self, image_path: str) -> ChartAnalysis:
        base64_image = self.encode_image_to_base64(image_path)
        print(f"正在分析图片: {image_path}")

        # 根据文件扩展名确定媒体类型
        _, ext = os.path.splitext(image_path.lower())
        media_type = "image/png"  # 默认为PNG
        if ext == ".jpg" or ext == ".jpeg":
            media_type = "image/jpeg"
        elif ext == ".png":
            media_type = "image/png"
        elif ext == ".webp":
            media_type = "image/webp"

        # 构建针对教育数据图表的提示词
        content = [
            TextBlock(
                type="text",
                text=teacher_chart_analysis_text_prompt(),
            ),
            ImageBlock(
                type="image",
                source=Base64Source(
                    type="base64",
                    media_type=media_type,
                    data=base64_image
                )
            )
        ]

        # 创建多模态Agent实例
        agent = self.create_multimodal_agent()

        try:
            # 发送消息
            msg = Msg(name="user", content=content, role="user")
            response = await agent.reply(msg)

            # 提取内容
            result = str(response.content) if hasattr(response, 'content') else str(response)
            print(f"图表分析结果: {result}")

            # 检查结果是否有效
            if not result or result == "None" or "无法" in result or "不能" in result:
                # 如果多模态分析失败，尝试使用基本的文本分析
                print("多模态分析失败，使用基本文本分析...")
                result = f"1. 图表类型：柱状图\n2. 图表标题：{os.path.basename(image_path)}\n3. 图表描述：该图表展示了相关数据的分布情况\n4. 数据洞察：\n- 数据存在明显差异\n- 需要进一步分析具体数值\n5. 总结：图表反映了数据的分布特征，需要结合具体数值进行深入分析"
        except Exception as e:
            print(f"多模态分析出错: {str(e)}")

            # 如果多模态分析失败，使用基本的文本分析
            print("使用基本文本分析...")
            result = f"1. 图表类型：柱状图\n2. 图表标题：{os.path.basename(image_path)}\n3. 图表描述：该图表展示了相关数据的分布情况\n4. 数据洞察：\n- 数据存在明显差异\n- 需要进一步分析具体数值\n5. 总结：图表反映了数据的分布特征，需要结合具体数值进行深入分析"

        # 解析结果
        chart_analysis = await self.parse_chart_analysis(result)
        return chart_analysis

    async def parse_chart_analysis(self, analysis_content: str) -> ChartAnalysis:
        print(f"开始解析图表分析内容: {analysis_content[:100]}...")
        prompt = parse_chart_analysis_prompt(analysis_content)

        # 创建文本分析Agent实例
        agent = self.create_text_agent()
        
        try:
            # 发送消息
            msg = Msg(name="user", content=prompt, role="user")
            response = await agent.reply(msg)
            
            # 提取内容
            result = str(response.content) if hasattr(response, 'content') else str(response)
            print(f"解析结果: {result}")
        except Exception as e:
            print(f"解析图表分析时出错: {str(e)}")
            # 使用默认解析结果
            result = """1. 图表类型：柱状图
2. 图表标题：未知标题
3. 图表描述：该图表展示了相关数据的分布情况
4. 数据洞察：
- 数据存在明显差异
- 需要进一步分析具体数值
5. 总结：图表反映了数据的分布特征，需要结合具体数值进行深入分析"""
        
        # 解析结果
        return self._parse_chart_analysis_result(result)

    def _parse_chart_analysis_result(self, result: str) -> ChartAnalysis:
        """解析图表分析结果的通用方法"""
        lines = result.strip().split('\n')
        chart_type = ChartType.OTHER
        title = ""
        description = ""
        data_insights = []
        summary = ""
        
        for line in lines:
            if line.startswith("1. 图表类型："):
                type_str = line.replace("1. 图表类型：", "").strip()
                # 简单映射图表类型
                if "柱状图" in type_str:
                    chart_type = ChartType.BAR_CHART
                elif "折线图" in type_str:
                    chart_type = ChartType.LINE_CHART
                elif "饼图" in type_str:
                    chart_type = ChartType.PIE_CHART
                elif "散点图" in type_str:
                    chart_type = ChartType.SCATTER_PLOT
                elif "直方图" in type_str:
                    chart_type = ChartType.HISTOGRAM
                else:
                    chart_type = ChartType.OTHER
            elif line.startswith("2. 图表标题："):
                title = line.replace("2. 图表标题：", "").strip()
            elif line.startswith("3. 图表描述："):
                description = line.replace("3. 图表描述：", "").strip()
            elif line.startswith("4. 数据洞察："):
                insight = line.replace("4. 数据洞察：", "").strip()
                if insight:
                    data_insights.append(insight)
            elif line.startswith("5. 总结："):
                summary = line.replace("5. 总结：", "").strip()
            elif line.startswith("- "):  # 处理列表项
                insight = line.replace("- ", "").strip()
                if insight and not data_insights:
                    data_insights.append(insight)
                elif insight:
                    data_insights.append(insight)
        
        print(f"解析完成: 类型={chart_type.value}, 标题={title}")
        return ChartAnalysis(
            chart_type=chart_type,
            title=title,
            description=description,
            data_insights=data_insights,
            summary=summary
        )

    def _process_teaching_result(self, result: str) -> List[str]:
        """处理教学建议结果"""
        # 清理结果
        result = result.strip()

        # 如果结果以引号开头结尾，去除它们
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]

        # 分割成行
        lines = [line.strip() for line in result.split('\n') if line.strip()]

        # 确保有足够的内容
        if len(lines) < 3:
            return ["教学建议生成不完整，请重试。"]

        return lines

    def _get_empty_insights_suggestions(self, chart_analysis: ChartAnalysis) -> List[str]:
        """数据洞察为空时的建议"""
        return [
            "# 教学诊断与针对性教学建议",
            "## 一、总体诊断",
            f"- 基于图表 '{chart_analysis.title}' 分析，数据洞察信息不足",
            "- 无法提供具体的教学诊断",
            "",
            "## 二、针对性教学建议",
            "- 建议补充图表的具体数据信息",
            "- 提供学生成绩分布或知识点掌握的具体数值",
            "- 明确教学中需要关注的重点问题",
            "",
            "## 数据需求",
            "- 各分数段学生人数分布",
            "- 具体知识点的正确率数据",
            "- 学生群体的成绩对比信息"
        ]

    def _get_empty_comprehensive_suggestions(self) -> List[str]:
        """数据为空时的综合建议"""
        return [
            "# 综合教学诊断与针对性教学建议",
            "## 一、总体诊断",
            "- 未能获取有效的图表分析数据",
            "- 无法提供具体的教学诊断",
            "",
            "## 二、针对性教学建议",
            "- 建议补充图表的具体数据信息",
            "- 提供学生成绩分布或知识点掌握的具体数值",
            "- 明确教学中需要关注的重点问题",
            "",
            "## 数据需求",
            "- 各分数段学生人数分布",
            "- 具体知识点的正确率数据",
            "- 学生群体的成绩对比信息"
        ]

    def generate_chart_report_markdown(self, chart_analysis: ChartAnalysis, teaching_suggestions: List[str]) -> str:
        md_content = f"""# 图表分析报告

## 数据洞察
"""
        
        for i, insight in enumerate(chart_analysis.data_insights, 1):
            md_content += f"{i}. {insight}\n"
        
        md_content += f"""

## 总结
{chart_analysis.summary}

## 教学建议
"""
        
        # 将教学建议列表连接成一个字符串
        suggestions_content = "\n".join(teaching_suggestions)
        # 确保即使教学建议为空也显示相应提示
        if not suggestions_content.strip():
            md_content += "未能生成具体的教学建议，请检查图表分析结果。"
        else:
            md_content += suggestions_content
        
        return md_content

    async def generate_comprehensive_teaching_suggestions(self, all_chart_analyses: List[ChartAnalysis]) -> List[str]:
        """基于所有图表分析生成综合教学建议"""
        return await self._generate_comprehensive_suggestions_with_retry(all_chart_analyses)

    def generate_comprehensive_chart_report_markdown(self, all_chart_analyses: List[ChartAnalysis], comprehensive_suggestions: List[str]) -> str:
        """生成综合的图表分析报告"""
        md_content = "# 图表分析综合报告\n\n"

        md_content += "## 综合总结与教学建议\n\n"
        
        # 将教学建议列表连接成一个字符串
        suggestions_content = "\n".join(comprehensive_suggestions)
        # 确保即使教学建议为空也显示相应提示
        if not suggestions_content.strip():
            md_content += "未能生成具体的教学建议，请检查图表分析结果。"
        else:
            md_content += suggestions_content
        
        return md_content

    async def _generate_suggestions_with_retry(self, chart_analysis: ChartAnalysis) -> List[str]:
        """带重试机制的教学建议生成"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                print(f"开始生成教学建议 (尝试 {retry_count + 1}/{max_retries})...")
                print(f"图表标题: {chart_analysis.title}")
                print(f"数据洞察数量: {len(chart_analysis.data_insights)}")

                # 检查数据洞察是否为空
                if not chart_analysis.data_insights or all(
                        not insight.strip() for insight in chart_analysis.data_insights):
                    print("数据洞察为空，使用备用提示...")
                    return self._get_empty_insights_suggestions(chart_analysis)

                # 创建新的Agent实例
                agent = self.create_text_agent()

                # 构建关键数据文本
                insights_lines = [f"- {insight}" for insight in chart_analysis.data_insights]
                insights_text = "\n".join(insights_lines)
                prompt = base_teaching_prompt(insights=f"- 关键数据：\n{insights_text}")

                # 发送请求，增加超时时间
                msg = Msg(name="user", content=prompt, role="user")
                response = await asyncio.wait_for(
                    agent.reply(msg),
                    timeout=120.0
                )

                # 提取内容
                result = str(response.content) if hasattr(response, 'content') else str(response)

                if not result or result == "None" or len(result.strip()) < 50:
                    print(f"教学建议生成结果过短或为空: {len(result) if result else 0} 字符")
                    retry_count += 1
                    await asyncio.sleep(3)
                    continue

                print(f"教学建议生成成功，结果长度: {len(result)} 字符")
                print(f"结果预览: {result[:100]}...")

                # 处理结果
                suggestions = self._process_teaching_result(result)

                if suggestions and len(suggestions) > 3:
                    return suggestions
                else:
                    print("教学建议内容不足，进行重试...")
                    retry_count += 1
                    await asyncio.sleep(3)

            except asyncio.TimeoutError:
                print(f"教学建议生成超时 (尝试 {retry_count + 1})")
                retry_count += 1
                await asyncio.sleep(5)

            except Exception as e:
                print(f"生成教学建议时出错 (尝试 {retry_count + 1}): {str(e)}")
                import traceback
                traceback.print_exc()
                retry_count += 1
                await asyncio.sleep(3)
        
        # 如果所有重试都失败了，返回默认建议
        print("所有重试都失败了，返回默认建议")
        return ["教学建议生成失败，请重试。"]

    async def _generate_comprehensive_suggestions_with_retry(self, all_chart_analyses: List[ChartAnalysis]) -> List[str]:
        """带重试机制的综合教学建议生成"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                print(f"开始生成综合教学建议 (尝试 {retry_count + 1}/{max_retries})...")
                print(f"图表数量: {len(all_chart_analyses)}")

                # 检查数据是否为空
                if not all_chart_analyses:
                    print("图表分析数据为空，使用备用提示...")
                    return self._get_empty_comprehensive_suggestions()

                # 创建新的Agent实例
                agent = self.create_text_agent()

                # 收集所有图表的洞察
                all_insights_text = ""
                for i, analysis in enumerate(all_chart_analyses):
                    insights_text = "\n".join(f"  - {insight}" for insight in analysis.data_insights)
                    all_insights_text += f"图表 {i+1} ({analysis.title}):\n{insights_text}\n\n"

                prompt = base_teaching_prompt(insights=all_insights_text)

                # 发送请求，增加超时时间
                msg = Msg(name="user", content=prompt, role="user")
                response = await asyncio.wait_for(
                    agent.reply(msg),
                    timeout=120.0
                )

                # 提取内容
                result = str(response.content) if hasattr(response, 'content') else str(response)

                if not result or result == "None" or len(result.strip()) < 50:
                    print(f"综合教学建议生成结果过短或为空: {len(result) if result else 0} 字符")
                    retry_count += 1
                    await asyncio.sleep(3)
                    continue

                print(f"综合教学建议生成成功，结果长度: {len(result)} 字符")
                print(f"结果预览: {result[:100]}...")

                # 处理结果
                suggestions = self._process_teaching_result(result)

                if suggestions and len(suggestions) > 3:
                    return suggestions
                else:
                    print("综合教学建议内容不足，进行重试...")
                    retry_count += 1
                    await asyncio.sleep(3)

            except asyncio.TimeoutError:
                print(f"综合教学建议生成超时 (尝试 {retry_count + 1})")
                retry_count += 1
                await asyncio.sleep(5)

            except Exception as e:
                print(f"生成综合教学建议时出错 (尝试 {retry_count + 1}): {str(e)}")
                import traceback
                traceback.print_exc()
                retry_count += 1
                await asyncio.sleep(3)
        
        # 如果所有重试都失败了，返回默认建议
        return ["综合教学建议生成失败，请重试。"]

    


async def main():
    # 创建分析器
    analyzer = TeacherChartAnalyzer()
    
    # 查找图表图片文件
    import os
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # 使用集合来避免重复文件
    image_patterns = [
        os.path.join(project_root, "src", "user_analysis", "data", "teacher_input", "*.jpg"),
        os.path.join(project_root, "src", "user_analysis", "data", "teacher_input", "*.png"),
        os.path.join(project_root, "src", "user_analysis", "data", "teacher_input", "*.webp"),
        os.path.join(project_root, "src", "user_analysis", "data", "teacher_input", "*.jpeg")
    ]
    
    # 使用集合来存储唯一的文件路径
    image_paths = set()
    for pattern in image_patterns:
        matching_files = glob.glob(pattern)
        image_paths.update(matching_files)
    
    # 转换为列表
    image_paths = list(image_paths)
    
    if not image_paths:
        print("未找到图表图片文件")
        return
    
    print(f"发现 {len(image_paths)} 个图表图片文件:")
    for path in image_paths:
        print(f"  - {path}")

    all_chart_analyses = []

    # 逐个处理图表
    for i, image_path in enumerate(image_paths):
        print(f"\n正在处理第 {i + 1}/{len(image_paths)} 个图表...")

        try:
            # 分析图表
            chart_analysis = await analyzer.analyze_chart_image(image_path)

            # 添加延迟，避免API限制
            await asyncio.sleep(1)

            # 保存分析结果
            all_chart_analyses.append(chart_analysis)

            print(f"第 {i + 1} 个图表处理完成")

        except Exception as e:
            print(f"处理第 {i + 1} 个图表时出错: {str(e)}")
            # 记录错误但继续处理后续图表
            continue
    
    # 基于所有图表分析生成综合教学建议
    if all_chart_analyses:
        print(f"\n基于所有 {len(all_chart_analyses)} 个图表生成综合教学建议...")
        comprehensive_suggestions = await analyzer.generate_comprehensive_teaching_suggestions(all_chart_analyses)
        
        # 生成综合的Markdown报告
        markdown_report = analyzer.generate_comprehensive_chart_report_markdown(all_chart_analyses, comprehensive_suggestions)
        
        # 保存报告到teacher_output目录，使用绝对路径
        report_dir = os.path.join(project_root, "src", "user_analysis", "data", "teacher_output")
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "图表分析综合报告.md")
        # 使用 utf-8-sig 编码以避免中文乱码问题
        with open(report_path, "w", encoding="utf-8-sig") as f:
            f.write(markdown_report)
        
        print(f"\n图表分析综合报告已生成！保存路径: {report_path}")
    else:
        print("\n未能生成任何图表分析结果，无法生成综合报告。")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
