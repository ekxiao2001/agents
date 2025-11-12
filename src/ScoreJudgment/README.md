# ScoreJudgment 模块说明

该模块用于对考生答案进行自动判分，并返回得分与判分理由。支持按题型进行差异化判分，其中“编程题”会在必要时执行用户代码进行正确性验证。

## 目录结构
- `score_judgment.py`：核心判分逻辑与 Agent 构造工厂 `build_score_judgment_agent`
- `schemas.py`：Pydantic 模型（`ScoreJudgmentInput`、`ScoreJudgmentOutput`、`GradingCriteriaInput` 等）
- `prompts.py`：系统提示与判分/细则生成的 Prompt 文本
- `conf.yaml`：模块内演示用的模型配置（仅 `__main__` 演示读取）

## 支持的题型
- `简答题`
- `编程题`

注意：`question_type` 仅支持以上两种取值。

## 输入与输出
- 输入（`ScoreJudgmentInput`）：
  - `question_title`：考试题目
  - `question_type`：`"简答题" | "编程题"`
  - `standard_answer`：题目标准答案
  - `student_answer`：考生答案
  - `full_score`：考题满分分数（必须 > 0）
  - `grading_criteria`：评分细则（可选；若未提供将自动生成）
- 输出（`ScoreJudgmentOutput`）：
  - `score`：考生得分（不超过 `full_score`）
  - `sj_reason`：判分理由（结构化说明得分与失分点）

## 配置说明
模块可绑定至不同大模型提供方：
- `LLM_BINDING`：`deepseek` 或 `dashscope`
- `MODEL_NAME`：模型名称
- `API_KEY`：对应提供方的密钥
- `BASE_URL`：DeepSeek 的接口地址（当绑定 `deepseek` 时需要）

优先推荐通过环境变量或仓库根目录的 `.env` 管理配置，避免将敏感密钥提交到版本库。`score_judgment.py` 的 `__main__` 演示会从本目录的 `conf.yaml` 读取上述配置，仅用于本地快速体验。

## Python 用法示例
通过工厂方法构造判分 Agent，并以异步方式调用：

```python
import asyncio
from src.ScoreJudgment.score_judgment import build_score_judgment_agent
from src.ScoreJudgment.schemas import ScoreJudgmentInput

agent = build_score_judgment_agent(
    llm_binding="deepseek",            # 或 "dashscope"
    model_name="deepseek-chat",        # 根据绑定方选择
    api_key="<YOUR_API_KEY>",          # 建议从环境变量读取
    base_url="https://api.deepseek.com",
    stream=False,
)

payload = ScoreJudgmentInput(
    question_title="请编写递归函数 fibonacci(n) 计算第 n 项",
    question_type="编程题",
    standard_answer=(
        "def fibonacci(n):\n"
        "    if n < 0:\n        return -1\n"
        "    elif n == 0:\n        return 0\n"
        "    elif n == 1:\n        return 1\n"
        "    else:\n        return fibonacci(n-1) + fibonacci(n-2)"
    ),
    student_answer=(
        "def fibonacci(n):\n"
        "    if n == 0:\n        return 0\n"
        "    elif n == 1:\n        return 1\n"
        "    else:\n        return fibonacci(n-1) + fibonacci(n-2)"
    ),
    full_score=10,
    # grading_criteria=None  # 可选：不提供时将自动生成
)

async def main():
    result = await agent.score_judgment(payload)
    print(result.score)
    print(result.sj_reason)

asyncio.run(main())
```

### 编程题的特殊处理
- 当 `question_type == "编程题"` 时，Agent 会注册并使用 `execute_python_code` 工具以验证程序可运行性及输出正确性（依据评分细则）。
- 若未提供 `grading_criteria`，系统将先调用细则生成器，编程题细则中会明确要求运行性与正确性验证。

## FastAPI 接口
服务在仓库根目录的 `fastapi_server_start.py` 中集成该模块，并提供以下端点：
- `POST /score-judgment`：判分接口

请求体（`ScoreJudgmentInput` 示例）：
```json
{
  "question_title": "请编写递归函数 fibonacci(n) 计算第 n 项",
  "question_type": "编程题",
  "standard_answer": "def fibonacci(n): ...",
  "student_answer": "def fibonacci(n): ...",
  "full_score": 10
}
```

响应体（`StandardResponse<ScoreJudgmentOutput>` 示例）：
```json
{
  "code": 0,
  "message": "判分成功",
  "data": {
    "score": 6,
    "sj_reason": "1) 得分点 ... 2) 失分点 ..."
  }
}
```

示例调用（默认端口参考 `.env` 为 `8022`）：
```bash
curl -X POST "http://localhost:8022/score-judgment" \
  -H "Content-Type: application/json" \
  -d '{
        "question_title": "请编写递归函数 fibonacci(n) 计算第 n 项",
        "question_type": "编程题",
        "standard_answer": "def fibonacci(n):...",
        "student_answer": "def fibonacci(n):...",
        "full_score": 10
      }'
```

## 日志
模块会在本目录自动创建 `logs/score_judgment.log`，使用滚动日志（每个文件最大约 5MB，最多保留 5 个）。

## 注意事项
- 确保 `full_score > 0`，并且最终得分不超过满分。
- 严格使用 `question_type` 的有效取值：`"简答题"` 或 `"编程题"`。
- 请勿将真实 `API_KEY` 提交到版本库，建议使用环境变量或 `.env` 管理。

## 本地快速演示
可直接运行本模块演示脚本（读取 `conf.yaml`）：

```bash
python src/ScoreJudgment/score_judgment.py
```