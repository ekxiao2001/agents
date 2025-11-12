# ExamSettingsExtraction 模块

面向“考试设置”信息抽取的模块。它从非结构化文本中提取考试关键设定，如考试时间、时长、入场/禁止入场时间、交卷时间限制、及格线等。支持作为 Python 库调用，且在项目的 FastAPI 服务中提供统一接口。

## 目录结构
- `exam_settings_extraction.py`：核心逻辑，`ExamSettingsExtractionAgent` 的实现与构建函数 `build_exam_settings_agent`。
- `schemas.py`：Pydantic 数据模型定义：`ExamSettingsInput`、`ExamSettingsOutput`、`StandardResponse`。
- `prompts.py`：系统提示与抽取指令模板。
- `conf.yaml`：默认模型配置（可用环境变量覆盖）。

## 抽取字段
- `exam_time`：考试时间，例如 `2024-01-15 14:00-16:00`。
- `duration`：考试时长，例如 `90分钟`、`2小时30分钟`。
- `early_entry_time`：允许提前入场时间，例如 `30`（分钟）。
- `late_entry_deadline`：开考后禁止入场时间，例如 `15`（分钟）。
- `submission_time_setting`：允许交卷的时间限制，例如 `30`（分钟，指剩余 30 分钟后可交卷）。
- `passing_score_percentage`：及格线设置，例如 `60%`、`70%`。

说明：上述字段在 `schemas.py` 中均为 `Optional[str]` 类型，以便兼容不同表达形式（数值或中文短语）。

## 数据模型
- `ExamSettingsInput`
  - `text_content`：包含考试设置信息的原始文本。
- `ExamSettingsOutput`
  - 见“抽取字段”，均为可选字符串；未抽到信息时为 `null`。
- `StandardResponse`
  - 统一响应封装（`code`、`message`、`data`）。

## 主要能力
- `ExamSettingsExtractionAgent.extract_settings(exam_settings_input: ExamSettingsInput) -> ExamSettingsOutput`
  - 基于提示与结构化输出，将模型响应映射为 `ExamSettingsOutput`。
- `build_exam_settings_agent(llm_binding, model_name, api_key, base_url, stream) -> ExamSettingsExtractionAgent`
  - 按配置创建可复用的抽取器实例；支持 `deepseek` 与 `dashscope`。

## 配置（conf.yaml）
- `LLM_BINDING`：`deepseek` 或 `dashscope`
- `MODEL_NAME`：例如 `deepseek-chat` 或 `qwen-max`
- `API_KEY`：模型 API Key（可通过环境变量覆盖）
- `BASE_URL`：DeepSeek 使用时可设置自定义地址

## Python 使用示例
```python
import asyncio
from src.ExamSettingsExtraction.exam_settings_extraction import build_exam_settings_agent
from src.ExamSettingsExtraction.schemas import ExamSettingsInput

agent = build_exam_settings_agent(
    llm_binding="dashscope",  # 或 "deepseek"
    model_name="qwen-max",
    api_key="<YOUR_API_KEY>",
    base_url="https://api.deepseek.com",  # deepseek 时需要
    stream=False,
)

input_ = ExamSettingsInput(
    text_content=(
        "本次期末考试时间为2024年1月15日 14:00-16:00，考试时长为120分钟。"
        "允许提前30分钟入场，开考后15分钟禁止入场。考试剩余30分钟可交卷，及格线为60%。"
    )
)

output = asyncio.run(agent.extract_settings(input_))
print(output.model_dump())
```

## FastAPI 接口
服务在仓库根目录的 `fastapi_server_start.py` 中集成该模块，并提供以下端点：
- `POST /exam-settings`：考试设置提取接口

请求体（`ExamSettingsInput` 示例）：
```json
{
  "text_content": "本次期末考试时间为2024年1月15日 14:00-16:00，考试时长为120分钟。允许提前30分钟入场，开考后15分钟禁止入场。考试剩余30分钟可交卷，及格线为60%。"
}
```

响应体（`StandardResponse<ExamSettingsOutput>` 示例）：
```json
{
  "code": 0,
  "message": "考试设置提取成功",
  "data": {
    "exam_time": "2024-01-15 14:00-16:00",
    "duration": "120分钟",
    "early_entry_time": "30",
    "late_entry_deadline": "15",
    "submission_time_setting": "30",
    "passing_score_percentage": "60%"
  }
}
```

示例调用（默认端口参考 `.env`）：
```bash
curl -X POST "http://localhost:8000/exam-settings" \
  -H "Content-Type: application/json" \
  -d '{
        "text_content": "本次期末考试时间为2024年1月15日 14:00-16:00，考试时长为120分钟。允许提前30分钟入场，开考后15分钟禁止入场。考试剩余30分钟可交卷，及格线为60%。"
      }'
```

## 实现细节
- 使用 `structured_model=ExamSettingsOutput`，由 Agentscope 自动校验并填充结构化输出；提取结果通过 `res.metadata` 读取。
- 提示模板在 `prompts.py` 中，要求严格输出包含全部字段的 JSON；若某字段不存在则为 `null`。

## 注意事项
- `schemas.py` 将所有字段定义为字符串以兼容不同表达形式；如果希望强制数字格式（例如分钟），可在接口层追加转换与校验。
- 请勿将真实 `API_KEY` 提交到版本库；生产环境建议通过环境变量或 `.env` 管理密钥。
- 不同模型的输出风格可能影响抽取稳定性，可根据需要微调提示或启用流式/非流式模式。

## 本地快速演示
- 运行：`python src/ExamSettingsExtraction/exam_settings_extraction.py`
- 或通过统一服务：`python fastapi_server_start.py` 后调用 `POST /exam-settings` 接口。