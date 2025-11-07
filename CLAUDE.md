# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **FastAPI-based AI agent service** that provides two core capabilities:
1. **Exam Question Verification** - Validates exam questions for compliance and provides automated fixes
2. **Score Judgment** - Scores student answers against grading criteria and generates scoring rubrics

The system uses the [AgentScope](https://github.com/microsoft/agentscope) framework and supports LLM providers (DeepSeek, DashScope). All services run in Docker containers orchestrated by Supervisor.

## Quick Start Commands

### Starting the Service
```bash
# Prepare sandbox images (one-time setup)
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-base:latest
docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-base:latest agentscope/runtime-sandbox-base:latest

docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-gui:latest
docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-gui:latest agentscope/runtime-sandbox-gui:latest

docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-filesystem:latest
docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-filesystem:latest agentscope/runtime-sandbox-filesystem:latest

docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-browser:latest
docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-browser:latest agentscope/runtime-sandbox-browser:latest

# Start all services
docker-compose up -d --build
```

**Note:** Initial startup may take time as uv installs dependencies.

### Stopping the Service
```bash
docker-compose down
```

### Viewing Logs
```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f fastapi_server
docker-compose logs -f eqv_agent_runtime
docker-compose logs -f runtime_sandbox_server

# View supervisor logs inside container
docker exec -it zhihui_agents tail -f /var/log/supervisor/*.log
```

### Testing
```bash
# Run the exam verification API test
cd /home/ercon/Desktop/simpleWare/agents/zhihui_agents
python test/eqv_fastapi_test.py

# Run the agent runtime test
python test/eqv_runtime_test.py
```

## High-Level Architecture

### Service Architecture
The system runs three services managed by Supervisor (`supervisord.conf`):

1. **Runtime Sandbox Server** (port 8010) - Docker-based sandbox for safe code execution
   - Entry point: `runtime_sandbox_server/sandbox_server.sh`
   - Configuration: `runtime_sandbox_server/conf.env`
   - Docker Compose: `runtime_sandbox_server/docker-compose.yml`

2. **EQV Agent Runtime** (port 8021) - Exam verification agent service
   - Main file: `agent_runtime/eqv_agent_runtime.py`
   - Runs as: `uv run -m agent_runtime.eqv_agent_runtime`

3. **FastAPI Server** (port 8022) - Main API gateway
   - Main file: `fastapi_server_start.py`
   - Entry point: `uv run fastapi_server_start.py`

### Module Structure

**`src/ExamQuestionVerification/`** - Exam Question Verification Module
- `exam_question_verification.py` - Core verification logic with iterative fix loop
- `eqv_agent.py` - AgentScope ReActAgent implementation
- `eqv_agent_runtime.py` - Runtime service entry point
- `prompts.py` - Verification prompts for different question types
- `schemas.py` - Pydantic models (ExamQuestion, VerificationResult, FixRequest)
- `conf.yaml` - Module-specific configuration

**`src/ScoreJudgment/`** - Score Judgment Module
- `score_judgment.py` - Core scoring logic
- `prompts.py` - Scoring and criteria generation prompts
- `schemas.py` - Pydantic models (ScoreJudgmentInput, ScoreJudgmentOutput, GradingCriteriaInput)
- `conf.yaml` - Module-specific configuration

### API Endpoints

**Exam Verification (考题检修)**
- `POST /eqv` - Verify exam question compliance
- `POST /eqf` - Fix exam question based on verification results

**Score Judgment (判题)**
- `POST /score-judgment` - Score student answers
- `POST /grading-criteria` - Generate grading criteria

**Health Checks**
- `GET /` - Welcome page
- `GET /health` - Health check

## Development Workflow

### 1. Environment Configuration
All configuration is in `.env`:
- LLM settings (provider, model, API key, base URL)
- FastAPI host/port (default: 8022)
- Agent runtime port (default: 8021)
- Sandbox settings (type: docker/local/remote, host, port: 8010)

### 2. Code Structure Patterns
- Each module has a `build_*_agent()` factory function that constructs the agent with model and formatter
- Agents use ReActAgent from AgentScope with InMemoryMemory
- All Pydantic schemas defined in `schemas.py` files
- Prompt templates in `prompts.py` with format placeholders
- Configuration in `conf.yaml` files for each module

### 3. Model Binding
The system supports two LLM providers via `LLM_BINDING` environment variable:
- `deepseek` - Uses DeepSeek API
- `dashscope` - Uses DashScope API

Models are configured in `fastapi_server_start.py:38-60` with conditional binding.

### 4. Docker Architecture
- Based on `python:3.10-slim`
- Installs Rust and uv for package management
- Uses domestic mirrors (Aliyun, Tsinghua) for faster downloads
- Mounts Docker socket for sandbox execution
- Multi-stage build with layer caching for dependencies

## Key Components

### AgentScope Integration
The project uses AgentScope for AI agents:
- `ReActAgent` for reasoning and acting
- `InMemoryMemory` for conversation history
- Formatter classes: `DeepSeekChatFormatter`, `DashScopeChatFormatter`
- Model classes: `OpenAIChatModel`, `DashScopeChatModel`

### Verification Process
The exam verification follows an iterative loop (`exam_question_verification.py:28-58`):
1. Verify current question
2. Check compliance flag
3. If non-compliant, fix and iterate (max 3 attempts)
4. Return final question

### Container Orchestration
All services are managed by Supervisor:
- Auto-restart on failure
- Separate log files for each service
- Nodaemon mode to keep container alive

## Testing
Test files are in `/test/`:
- `eqv_fastapi_test.py` - Tests FastAPI endpoints
- `eqv_runtime_test.py` - Tests agent runtime service

## Important Configuration Files

- `.env` - Environment variables and API keys
- `docker-compose.yml` - Service orchestration
- `Dockerfile` - Container image build
- `supervisord.conf` - Service management
- `pyproject.toml` - Python dependencies (uv format)

## Common Development Tasks

### Modifying Exam Verification Logic
Edit: `src/ExamQuestionVerification/exam_question_verification.py`

### Adding New Question Types
1. Add type to schema in `src/ExamQuestionVerification/schemas.py`
2. Add verification prompt in `src/ExamQuestionVerification/prompts.py:1`
3. Add conditional logic in `exam_question_verification.py:78-93`

### Changing LLM Provider
Update `.env:1`:
```
LLM_BINDING=dashscope  # or deepseek
MODEL_NAME=your-model
API_KEY=your-key
BASE_URL=your-url
```

### Debugging
```bash
# View real-time logs
docker-compose logs -f

# Access container shell
docker exec -it zhihui_agents /bin/bash

# Check service status
docker-compose ps
```

## Notes

- The system uses iterative verification with a maximum of 3 fix attempts
- All timestamps and logs are in Chinese
- The sandbox requires Docker socket access for code execution
- Dependencies are managed by uv, not pip