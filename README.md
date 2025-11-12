# zhihui_agents 项目说明

统一的考试类智能体服务，集成三大能力：
- 考题检修（核查与修复）
- 判题（自动评分与细则生成）
- 考试设置提取（从文本中提取考试设定）

对外通过 FastAPI 暴露统一接口；容器内由 Supervisor 管理三项服务：Runtime Sandbox Server（沙箱）、EQV(ExamQuestionVerification, 考题核查) Agent Runtime（智能体运行时）与 FastAPI Server（网关）。

## 目录结构
- `fastapi_server_start.py`：统一 API 网关与端点定义
- `docker-compose.yml`：一键启动三项服务（映射 8010/8021/8022）
- `Dockerfile`：容器镜像构建（安装 Rust、uv、Supervisor 等）
- `supervisord.conf`：三项服务的进程管理配置
- `.env`：统一环境变量（LLM、FastAPI、Agent Runtime、Sandbox）
- `agent_runtime/`：EQV Agent Runtime 启动脚本
- `runtime_sandbox_server/`：沙箱服务（容器管理、配置）
- `src/`：业务模块
  - `ExamQuestionVerification/`：考题核查与修复
  - `ScoreJudgment/`：自动判分与细则生成
  - `ExamSettingsExtraction/`：考试设置提取

## 服务架构
容器内由 Supervisor 启动并管理以下服务：
- Runtime Sandbox Server（端口 `8010`）
  - 入口：`runtime_sandbox_server/sandbox_server.sh`
  - 配置：`runtime_sandbox_server/conf.env`
  - 职责：通过挂载宿主机 Docker Socket 管理沙箱容器，供智能体执行代码等高风险操作
- EQV Agent Runtime（端口 `8021`）
  - 入口：`agent_runtime/eqv_agent_runtime.py`
  - 路径：`AGENT_RUNTIME_ENDPOINT_PATH`（默认 `/eqv_agent`）
  - 职责：将考题核查/修复能力封装为可部署的 AgentScope Runtime 服务
- FastAPI Server（端口 `8022`）
  - 入口：`fastapi_server_start.py`
  - 职责：统一对外 HTTP 接口（健康检查、考题检修、判题、考试设置）

所有服务的启动命令与日志路径见 `supervisord.conf`。

## 环境变量（.env）
- LLM 模型绑定：`LLM_BINDING`（`deepseek` 或 `dashscope`）、`MODEL_NAME`、`API_KEY`、`BASE_URL`（DeepSeek 需设定）
- FastAPI：`FASTAPI_HOST`、`FASTAPI_PORT`（默认 `8022`）
- Agent Runtime：`AGENT_RUNTIME_HOST`、`AGENT_RUNTIME_PORT`（默认 `8021`）、`AGENT_RUNTIME_ENDPOINT_PATH`
- Sandbox：`AGENT_RUNTIME_SANDBOX_TYPE`（`local`/`docker`/`remote`）、`AGENT_RUNTIME_SANDBOX_HOST`、`AGENT_RUNTIME_SANDBOX_PORT`（默认 `8010`）

沙箱服务详细配置见 `runtime_sandbox_server/conf.env`，包括：
- `HOST`、`PORT`、`WORKERS`、`DEBUG`
- `DEFAULT_SANDBOX_TYPE`（默认 `["base"]`）与 `POOL_SIZE`
- 端口范围 `PORT_RANGE`、容器前缀 `CONTAINER_PREFIX_KEY`
- 可选 Redis/OSS/K8S 设置

## FastAPI 端点
应用元信息与端点定义位于 `fastapi_server_start.py`，默认启用跨域（CORS 允许所有）。

- `GET /` 欢迎页，返回服务欢迎信息
- `GET /health` 健康检查

- `POST /eqv`（标签：考题检修）
  - 入参：`ExamQuestion`
  - 出参：`StandardResponse` 包含 `VerificationResult`
- `POST /eqf`（标签：考题检修）
  - 入参：`FixRequest`
  - 出参：`StandardResponse` 包含修正后的 `ExamQuestion`

- `POST /score-judgment`（标签：判题）
  - 入参：`ScoreJudgmentInput`
  - 出参：`StandardResponse` 包含 `ScoreJudgmentOutput`
- `POST /grading-criteria`（标签：判题）
  - 入参：`GradingCriteriaInput`
  - 出参：`StandardResponse` 包含 `{ grading_criteria: str }`

- `POST /exam-settings`（标签：考试设置）
  - 入参：`ExamSettingsInput`
  - 出参：`StandardResponse` 包含 `ExamSettingsOutput`

访问 `http://localhost:8022/docs` 可查看交互文档与在线调试。

## 示例请求（curl）
考题核查：
```bash
curl -X POST "http://localhost:8022/eqv" \
  -H "Content-Type: application/json" \
  -d '{
        "question": "请解释 BFS 与 DFS 的差异...",
        "answer": "BFS 层序遍历...",
        "answer_analysis": "...",
        "question_type": "简答题",
        "knowledge_point": "图搜索",
        "knowledge_point_description": "广度/深度遍历基础",
        "extra_requirement": ""
      }'
```

考题修复：
```bash
curl -X POST "http://localhost:8022/eqf" \
  -H "Content-Type: application/json" \
  -d '{
        "exam_question": { "question": "...", "answer": "...", "answer_analysis": "...", "question_type": "简答题", "knowledge_point": "...", "knowledge_point_description": "...", "extra_requirement": "" },
        "verification_result": { "is_compliant": false, "suggestion": "题型不匹配，建议..." }
      }'
```

判分：
```bash
curl -X POST "http://localhost:8022/score-judgment" \
  -H "Content-Type: application/json" \
  -d '{
        "question_title": "请编写递归函数 fibonacci(n)",
        "question_type": "编程题",
        "standard_answer": "def fibonacci(n):...",
        "student_answer": "def fibonacci(n):...",
        "full_score": 10
      }'
```

评分细则生成：
```bash
curl -X POST "http://localhost:8022/grading-criteria" \
  -H "Content-Type: application/json" \
  -d '{
        "question_title": "请编写递归函数 fibonacci(n)",
        "question_type": "编程题",
        "standard_answer": "def fibonacci(n):...",
        "full_score": 10
      }'
```

考试设置提取：
```bash
curl -X POST "http://localhost:8022/exam-settings" \
  -H "Content-Type: application/json" \
  -d '{
        "text_content": "期末考试时间为2024年1月15日 14:00-16:00，时长120分钟。允许提前30分钟入场，开考后15分钟禁止入场。考试剩余30分钟可交卷，及格线为60%。"
      }'
```

## 本地运行（开发模式）
项目使用 `uv` 管理依赖。建议本地安装 `uv` 并同步依赖：

```bash
# 可选择安装 uv（或直接使用 pip，见下方）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步依赖（使用 uv.lock）
uv sync --frozen --no-dev

# 启动 FastAPI（默认 0.0.0.0:8022）
python fastapi_server_start.py
```

如果使用 `pip`，请自行安装服务依赖（FastAPI/uvicorn/dotenv 等）：
```bash
pip install agentscope agentscope-runtime pydantic pyyaml fastapi uvicorn python-dotenv
python fastapi_server_start.py
```

## 容器部署（生产/集成）
### 准备 Sandbox 镜像（建议预拉取）
```bash
# 基础镜像
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-base:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-base:latest agentscope/runtime-sandbox-base:latest

# GUI 镜像
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-gui:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-gui:latest agentscope/runtime-sandbox-gui:latest

# 文件系统镜像
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-filesystem:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-filesystem:latest agentscope/runtime-sandbox-filesystem:latest

# 浏览器镜像
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-browser:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-browser:latest agentscope/runtime-sandbox-browser:latest
```

### 一键启动
```bash
docker-compose up -d --build
```

容器首次启动会使用 `uv` 安装依赖，可能需要一定时间。容器名称默认为 `zhihui_agents`。

### 端口与挂载
- 映射端口：`8010:8010`（Sandbox）、`8021:8021`（Agent Runtime）、`8022:8022`（FastAPI）
- 挂载：Docker Socket（`/var/run/docker.sock`）与 Docker CLI（`/usr/bin/docker`）以使容器内可控制宿主机 Docker

### 查看日志
```bash
# 所有服务日志
docker-compose logs -f

# 单服务日志
docker-compose logs -f fastapi_server
docker-compose logs -f eqv_agent_runtime
docker-compose logs -f runtime_sandbox_server

# 容器内 Supervisor 日志
docker exec -it zhihui_agents tail -f /var/log/supervisor/*.log
```

## 模型绑定与说明
- 设置 `LLM_BINDING=deepseek` 或 `dashscope`
- `MODEL_NAME` 与 `API_KEY` 必填；DeepSeek 需设置 `BASE_URL=https://api.deepseek.com`
- 代码中统一通过构建函数注入模型与格式化器：
  - `build_exam_verifier(...)`
  - `build_score_judgment_agent(...)`
  - `build_exam_settings_agent(...)`

## 模块概览
- `ExamQuestionVerification`：核查 JSON 字段包含 `question/answer/...`；支持多题型；提供核查、修复与合成流程
- `ScoreJudgment`：根据题型与评分细则评分；编程题自动注册执行代码工具；支持细则生成
- `ExamSettingsExtraction`：从自然语言文本抽取考试设置六字段（时间、时长、入场/截止、交卷、及格线）

各模块的详细接口、示例与注意事项，见对应目录下的 `README.md`。
