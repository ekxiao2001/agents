# 考试生成模块（exam_generation）

本模块提供两类能力：
- 多题型试卷生成：根据课程名称与题型配置生成完整试卷与答案（Markdown）。
- 基于知识点的考题生成：根据课程、知识点或自由描述生成结构化题目（JSON）。

## 目录结构
- `prompts.py`：提示词模板与构造函数。
- `multi_type_paper_generator.py`：多题型试卷生成器。
- `knowledge_question_generator.py`：知识点驱动的考题生成器。
- `router.py`：FastAPI 路由与接口封装。
- `schemas.py`：Pydantic 请求与响应模型。
- `conf.yaml`：模块级 LLM 配置（可被环境变量覆盖）。
- `__init__.py`

## 快速开始（Python）
- 试卷生成器（返回试卷与答案 Markdown）：

```python
import asyncio
from src.exam_generation.multi_type_paper_generator import MultiTypePaperGenerator

async def run():
    gen = MultiTypePaperGenerator()
    question_types = [
        {"index": "一", "type": "选择题", "count": 10, "score": 2},
        {"index": "二", "type": "简答题", "count": 5, "score": 8},
    ]
    paper_md, answers_md = await gen.generate_full_paper("数据结构", question_types)
    print(paper_md[:200])
    print(answers_md[:200])

asyncio.run(run())
```

- 考题生成器（返回题目 JSON 文本或原始字符串）：

```python
import asyncio
from src.exam_generation.knowledge_question_generator import KnowledgeBasedQuestionGenerator

async def run():
    gen = KnowledgeBasedQuestionGenerator()
    topic = "算法设计与分析"
    kps = ["动态规划基本思想", "最优子结构"]
    res = await gen.generate_questions(
        topic=topic,
        knowledge_points=kps,
        question_type="选择题",
        count=3,
        description=""
    )
    print(res[:300])

asyncio.run(run())
```

## FastAPI 接口
该模块已在根目录 `fastapi_server_start.py` 中集成并注册，默认前缀为 `/exam-generation`。

- `POST /exam-generation/paper_generate`：生成多题型试卷
  - 请求体（`GeneratePaperRequest`）示例：
    ```json
    {
      "topic": "数据结构",
      "question_types": [
        {"index":"一","type":"选择题","count":10,"score":2},
        {"index":"二","type":"简答题","count":5,"score":8}
      ]
    }
    ```
  - 响应（`GenerateResponse`）包含：`paper_content`、`answer_content` 以及 `file_paths`。

- `GET /exam-generation/paper_get_cached_input/{topic}`：获取指定课程的缓存输入

- `POST /exam-generation/question_generate`：生成考题
  - 方式一（仅自由描述）：
    ```json
    {"description":"请为《算法设计与分析》生成1道关于动态规划的选择题"}
    ```
  - 方式二（结构化字段）：
    ```json
    {
      "topic":"算法设计与分析",
      "knowledge_points":["动态规划基本思想","最优子结构"],
      "question_type":"选择题",
      "count":3,
      "difficulty":"一般"
    }
    ```
  - 响应：包含 `success`、`data` 以及 `file_path`（落盘路径）。当无法解析为 JSON 时 `data.raw_content` 返回原始字符串。

## 配置
- 模块内 `conf.yaml` 提供默认配置：
  - `LLM_BINDING`：`deepseek` 或 `dashscope`
  - `MODEL_NAME`：模型名称
  - `API_KEY`：密钥（建议使用环境变量，不要提交真实密钥）
  - `BASE_URL`：DeepSeek 需设置兼容地址
- 环境变量可覆盖上述值：`LLM_BINDING`、`MODEL_NAME`、`API_KEY`、`BASE_URL`。
- 推荐通过仓库根目录 `.env` 管理密钥，避免将敏感信息写入版本库。

## 文件输出
- 试卷与答案保存目录：`generated_papers/`，文件名形如：
  - `试卷_<课程>_<时间戳>.md`
  - `试卷答案_<课程>_<时间戳>.md`
- 考题保存目录：`generated_questions/`，文件名形如：
  - `考题_需求描述_<时间戳>.json`
  - `考题_<课程>_<题型>_<时间戳>.json`

## 关键实现与参考
- 试卷生成入口：`generate_full_paper`（`src/exam_generation/multi_type_paper_generator.py`）
- 考题生成入口：`generate_questions`（`src/exam_generation/knowledge_question_generator.py`）
- 提示词构造：`prompts.py` 提供系统提示、试卷与答案提示、题目合成提示。
- FastAPI 路由与落盘逻辑：`src/exam_generation/router.py`
- 请求/响应模型：`src/exam_generation/schemas.py`

## 注意事项
- 保证 LLM 配置有效并有可用额度。
- 真实密钥请使用环境变量或 `.env` 注入，避免提交到仓库。
- 当返回内容以 `"试卷生成失败:"` 或 `"考题生成失败:"` 开头时表明生成失败，请检查配置或网络。