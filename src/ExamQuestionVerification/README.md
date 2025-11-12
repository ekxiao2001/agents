# ExamQuestionVerification 模块

面向考试题目质量控制的核查与修正模块。它支持对题目进行合规性检查（题型匹配、完整性、答案与解析严谨性、知识点与额外要求符合度），并在不合规时生成修正建议，或直接产出修正后的考题。模块既可作为 Python 库调用，也可通过 Agent 运行时与 FastAPI 服务对外提供接口。

## 目录结构
- `exam_question_verification.py`：核心业务逻辑，提供 `verify_exam_question`、`fix_exam_question`、`verify_and_fix_exam_question` 以及 `build_exam_verifier`。
- `eqv_agent.py`：将业务能力封装为 `ReActAgent`，注册工具函数 `exam_question_verify_tool` 与 `exam_question_fix_tool`。
- `eqv_agent_runtime.py`：基于 `agentscope_runtime` 的可部署 AgentRuntime，支持本地或远程沙箱、流式输出与本地部署。
- `schemas.py`：Pydantic 数据模型定义，包括 `ExamQuestion`、`VerificationResult`、`FixRequest`、`VerifyAndFixRequest`、`StandardResponse`。
- `prompts.py`：系统提示词与不同题型的核查/修正模板。
- `conf.yaml`：模型与运行参数配置。

## 支持题型
- `单选题`、`填空题`、`简答题`、`计算题`、`编程题`
- 对未显式支持的题型，将回退使用通用核查模板。

## 输入输出规范

- `ExamQuestion`（题目信息）
  - `question`：题干，字符串，至少 5 个字符
  - `answer`：正确答案内容，字符串
  - `question_type`：题型，取值之一：`单选题`、`填空题`、`简答题`、`计算题`、`编程题`
  - `answer_analysis`：答案解析，字符串
  - `knowledge_point`：知识点（可选）
  - `knowledge_point_description`：知识点描述（可选）
  - `extra_requirement`：额外要求（可选）

- `VerificationResult`（核查结果）
  - `is_compliant`：是否合规，布尔
  - `suggestion`：修正建议，字符串或空

## 主要能力

- `verify_exam_question(exam_question: ExamQuestion) -> VerificationResult`
  - 针对题型选择对应核查模板（或通用模板），返回是否合规与修正建议。
- `fix_exam_question(exam_question: ExamQuestion, verification_result: VerificationResult) -> ExamQuestion`
  - 当不合规时，根据建议生成修正后的考题（覆盖题干/答案/解析/题型/知识点等）。
- `verify_and_fix_exam_question(exam_question: ExamQuestion, max_fix_attempts: int = 3) -> ExamQuestion`
  - 先核查，若不合规则按建议迭代修正，最多修正 `max_fix_attempts` 次，返回最终题目。
- `build_exam_verifier(...) -> ExamQuestionVerification`
  - 根据 `LLM_BINDING`、`MODEL_NAME`、`API_KEY` 等创建 `ExamQuestionVerification` 实例。

## 配置（conf.yaml）
- `LLM_BINDING`：`deepseek` 或 `dashscope`
- `MODEL_NAME`：如 `deepseek-chat` 或 `qwen-max`
- `API_KEY`：模型的 API Key（可通过环境变量覆盖）
- `BASE_URL`：`deepseek` 使用时可配置自定义地址
- `MAX_FIX_ATTEMPTS`：`verify_and_fix_exam_question` 的默认最大修复次数（示例为 3）
- Agent Runtime：
  - `AGENT_RUNTIME_HOST`、`AGENT_RUNTIME_PORT`、`AGENT_RUNTIME_ENDPOINT_PATH`
  - 远程沙箱可选：`AGENT_RUNTIME_SANDBOX_TYPE`、`AGENT_RUNTIME_SANDBOX_HOST`、`AGENT_RUNTIME_SANDBOX_PORT`

## Python 使用示例

```python
from ExamQuestionVerification.exam_question_verification import build_exam_verifier
from ExamQuestionVerification.schemas import ExamQuestion

verifier = build_exam_verifier(
    llm_binding="dashscope",   # 或 "deepseek"
    model_name="qwen-max",
    api_key="<YOUR_API_KEY>",
    base_url="https://api.deepseek.com",  # deepseek 时可用
    stream=False,
)

exam = ExamQuestion(
    question="请解释 BFS 与 DFS 的遍历差异，并给出典型适用场景。",
    answer="BFS 层序遍历适用于最短路径；DFS 纵深适用于拓扑或连通分量。",
    answer_analysis="……",
    question_type="简答题",
    knowledge_point="图搜索",
    knowledge_point_description="广度/深度遍历基础",
    extra_requirement="",
)

# 仅核查
res = await verifier.verify_exam_question(exam)
print(res.is_compliant, res.suggestion)

# 核查并自动修正
fixed = await verifier.verify_and_fix_exam_question(exam, max_fix_attempts=3)
print(fixed.model_dump())
```

## Agent 封装与工具函数

- 在 `eqv_agent.py` 中，业务能力封装为 `ExamQuestionVerificationAgent`：
  - `exam_question_verify_tool(...)`：入参为题目各字段，返回核查结果 JSON 文本。
  - `exam_question_fix_tool(...)`：在给定修正建议的情况下，返回修正后的题目 JSON 文本。

## Agent Runtime（可部署）

- `eqv_agent_runtime.py` 提供基于 `agentscope_runtime` 的运行时：
  - `connect(session_id, user_id, sandbox_type, sandbox_host, sandbox_port)`：连接会话、内存与沙箱。
  - `chat(session_id, user_id, chat_messages)`：流式推理接口（生成式聊天/工具调用）。
  - `deploy(host, port, endpoint_path)`：本地部署为 HTTP 服务，支持健康检查与流式输出。
  - 通过环境变量覆盖 `LLM_BINDING`、`MODEL_NAME`、`API_KEY`、`BASE_URL`。

## FastAPI 接口（参考）

在主工程的 `fastapi_server_start.py` 中可见集成的端点：
- `/eqv`：核查接口，入参为 `ExamQuestion`，返回 `VerificationResult`
- `/eqf`：修正接口，入参为 `FixRequest`，返回修正后的 `ExamQuestion`

示例请求（核查）：
```json
{
  "question": "……",
  "answer": "……",
  "answer_analysis": "……",
  "question_type": "简答题",
  "knowledge_point": "……",
  "knowledge_point_description": "……",
  "extra_requirement": ""
}
```

示例响应：
```json
{
  "is_compliant": false,
  "suggestion": "题型不匹配，建议将题干改为……"
}
```

示例请求（修正）：
```json
{
  "exam_question": { /* 题目信息 */ },
  "verification_result": { "is_compliant": false, "suggestion": "……" }
}
```

示例响应：
```json
{
  "question": "修正后的题干……",
  "answer": "修正后的答案……",
  "answer_analysis": "修正后的解析……",
  "question_type": "填空题",
  "knowledge_point": "……",
  "knowledge_point_description": "……",
  "extra_requirement": ""
}
```

## JSON 解析重试机制

为提升稳定性，`exam_question_verification.py` 使用 `_call_agent_with_json_retry` 封装：
- 首次按原始 prompt 调用；若解析失败，再次提示严格输出 JSON；最多重试 3 次。
- 当仍失败时返回默认结果（核查返回默认合规性为 `False` 与提示语；修正则回退到原题目）。

## 本地演示
- 直接运行 `eqv_agent.py` 中的 `main()` 可与代理交互（输入 `exit` 退出）。
- 运行时部署可用 `EQV_AgentRuntime.deploy(host, port, endpoint_path)` 在本地暴露 HTTP 服务。