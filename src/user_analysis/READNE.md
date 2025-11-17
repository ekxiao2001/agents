# 用户分析模块（user_analysis）

该模块提供两套能力：
- 学生答题卡分析：解析试卷答题卡 Markdown 文本或文件，提取题型与分数，汇总知识点掌握度并生成个性化学习建议与报告。
- 教师图表分析（多模态）：解析教学数据图表（图片），识别图表类型、提取教育数据洞察，并生成教学诊断与建议报告。

## 目录结构
- `student_analyzer.py`：学生答题卡分析器。
- `teacher_analyzer_multimodal.py`：教师图表多模态分析器。
- `router.py`：FastAPI 路由与接口封装。
- `schemas.py`：Pydantic 请求与响应模型。
- `prompts.py`：提示词模板与构造函数。
- `conf.yaml`：模块级 LLM 配置（可被环境变量覆盖）。
- `__init__.py`

## 学生答题卡分析（Python）
- 输入为试卷答题卡的 Markdown 文本，包含各题型标题、题目、分值、学生答案、正确答案等。

```python
import asyncio
from src.user_analysis.student_analyzer import StudentAnswerAnalyzer

async def run():
    content = """
    # 试卷标题
    ## 一、单选题（共20分） 得分：16
    ### 第1题
    题目内容...
    **学生答案**：A
    **正确答案**：B
    
    ### 第2题
    题目内容...
    **学生答案**：B
    **正确答案**：B
    
    ## 二、简答题（共40分） 得分：28
    ### 第1题
    题目内容...
    **学生答案**：...
    **正确答案**：...
    **答案解析**：...
    
    ## 考试总结
    """

    analyzer = StudentAnswerAnalyzer()
    report = analyzer.parse_answer_sheet(content)
    await analyzer._extract_knowledge_points_with_llm(report.sections)
    report.knowledge_mastery = await analyzer._analyze_knowledge_mastery_with_llm(report.sections)
    report.learning_suggestions = await analyzer._generate_learning_suggestions_with_llm(report)
    md = analyzer.generate_report_markdown(report)
    print(md[:300])

asyncio.run(run())
```

## 教师图表分析（Python）
- 输入为图表图片路径，返回图表结构化分析与教学建议。

```python
import asyncio
from src.user_analysis.teacher_analyzer_multimodal import TeacherChartAnalyzer

async def run():
    analyzer = TeacherChartAnalyzer()
    chart = await analyzer.analyze_chart_image("/path/to/chart.png")
    suggestions = await analyzer._generate_suggestions_with_retry(chart)
    md = analyzer.generate_chart_report_markdown(chart, suggestions)
    print(md[:300])

asyncio.run(run())
```

## FastAPI 接口
该模块已在根目录 `fastapi_server_start.py` 中集成，默认前缀 `/user-analysis`。

- `POST /user-analysis/student_analyze_file`：上传答题卡文件并分析
  - 入参：`multipart/form-data`，字段 `file`
  - 出参（`StudentAnalyzeResponse`）：总分、学生总分、各题型总结、知识点掌握度、学习建议、Markdown 报告与落盘路径

- `POST /user-analysis/student_analyze_content`：直接提交答题卡内容并分析
  - 入参：`text/plain` 内容
  - 出参：同上

- `POST /user-analysis/teacher_analyze_chart`：上传单张图表图片并分析
  - 入参：`multipart/form-data`，字段 `file`
  - 出参（`TeacherAnalyzeResponse`）：图表类型、标题、描述、数据洞察、总结、教学建议、Markdown 报告

- `POST /user-analysis/teacher_analyze_multiple_charts`：上传多张图表进行综合分析
  - 入参：`multipart/form-data`，字段 `files[]`
  - 出参（`TeacherMultipleAnalyzeResponse`）：各图结构化分析与综合教学建议、报告

## 配置
- 模块内 `conf.yaml` 支持：
  - `LLM_BINDING`：`deepseek` 或 `dashscope`
  - `MODEL_NAME`：模型名称
  - `API_KEY`：密钥（建议使用环境变量，不要提交真实密钥）
  - `BASE_URL`：DeepSeek 需设置兼容地址
  - 多模态：`MM_MODEL_BINDING`、`MM_MODEL_NAME`、`MM_MODEL_API_KEY`、`MM_MODEL_BASE_URL`
- 环境变量可覆盖上述值；推荐使用仓库根目录 `.env` 管理密钥。

## 文件输出
- 学生报告落盘目录：`data/学生端数据/`，文件名：`学生个性化学习报告_<时间戳>.md`
- 教师分析临时目录：`temp/`（上传图片会在此保存并在处理后删除）

## 关键实现与参考
- 学生分析入口：`StudentAnswerAnalyzer.parse_answer_sheet` 与后续 `_extract_knowledge_points_with_llm`、`_analyze_knowledge_mastery_with_llm`、`_generate_learning_suggestions_with_llm`、`generate_report_markdown`（`src/user_analysis/student_analyzer.py`）
- 教师分析入口：`TeacherChartAnalyzer.analyze_chart_image`、`_generate_suggestions_with_retry`、`generate_chart_report_markdown`、`generate_comprehensive_teaching_suggestions`（`src/user_analysis/teacher_analyzer_multimodal.py`）
- 路由与接口定义：`src/user_analysis/router.py`
- 请求/响应模型：`src/user_analysis/schemas.py`
- 提示词模板：`src/user_analysis/prompts.py`

## 注意事项
- 保证 LLM 配置有效并有可用额度。
- 避免提交真实密钥；优先使用环境变量或 `.env`。
- 答题卡解析依赖规范化的 Markdown 结构；若结构不一致，可能影响解析结果与评分统计。