import os
import asyncio
import socket
from typing import List, Dict, AsyncGenerator, Literal

from agentscope_runtime.engine.agents.agentscope_agent import AgentScopeAgent
from agentscope_runtime.engine import Runner
from agentscope_runtime.engine.services.session_history_service import InMemorySessionHistoryService
from agentscope_runtime.engine.services.memory_service import InMemoryMemoryService
from agentscope_runtime.engine.services.context_manager import ContextManager
from agentscope_runtime.engine.services.sandbox_service import SandboxService
from agentscope_runtime.engine.services.environment_manager import EnvironmentManager
from agentscope_runtime.engine.deployers.local_deployer import LocalDeployManager
from agentscope_runtime.engine.schemas.agent_schemas import (
    Message,
    RunStatus,
    AgentRequest,
)

from agentscope.model import OpenAIChatModel, DashScopeChatModel
from agentscope.formatter import DeepSeekChatFormatter, DashScopeChatFormatter

from .eqv_agent import ExamQuestionVerificationAgent
from .prompts import PROMPTS

# ---------------------------
# 加载配置文件
# ---------------------------
import yaml
conf_path = os.path.join(os.path.dirname(__file__), "conf.yaml")
with open(conf_path, "r", encoding="utf-8") as f:
    CONF = yaml.safe_load(f)


# ---------------------------
# 考试题目核查+修正工具实例构建
# ---------------------------
LLM_BINDING =  os.getenv("LLM_BINDING") or CONF.get("LLM_BINDING") or "deepseek"
MODEL_NAME = os.getenv("MODEL_NAME") or CONF.get("MODEL_NAME") or "deepseek-chat"
API_KEY = os.getenv("API_KEY") or CONF.get("API_KEY") or ""
BASE_URL = os.getenv("BASE_URL") or CONF.get("BASE_URL") or "https://api.deepseek.com"


class EQV_AgentRuntime:
    def __init__(
        self,
        llm_binding: str = LLM_BINDING,
        model_name: str = MODEL_NAME,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
    ) -> None:
        self.llm_binding = llm_binding
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url

        self.tools = None
        # from agentscope_runtime.sandbox.tools.base import run_ipython_cell
        # self.tools = [run_ipython_cell]

        self.agent = self.create_exam_question_verification_agent()

        self.connected = False

    async def connect(
        self,
        session_id: str, 
        user_id: str, 
        sandbox_type: Literal["local", "docker", "remote"] = "local",
        sandbox_host: str = "localhost",
        sandbox_port: int = 8010,
    ) -> None:
        """
        连接到沙箱环境，初始化会话历史、内存服务、沙箱服务和上下文管理器。
        Args:
            session_id: 会话历史服务和沙箱服务的会话ID
            user_id: 会话历史服务和沙箱服务的用户ID
            sandbox_type: 沙箱类型，可选值为 "local"（默认）、"docker" 或 "remote"
            sandbox_host: 远程沙箱服务的主机名，仅在 sandbox_type 为 "remote" 时使用，默认值为 "localhost"
            sandbox_port: 远程沙箱服务的端口号，仅在 sandbox_type 为 "docker" 或 "remote" 时使用，默认值为 8002
        """
        # 初始化会话历史服务
        session_history_service = InMemorySessionHistoryService()
        await session_history_service.create_session(session_id, user_id)

        # 初始化内存服务
        self.memory_service = InMemoryMemoryService()
        await self.memory_service.start()

        # 初始化沙箱
        if sandbox_type == "local":
            self.sandbox_service = SandboxService()
        elif sandbox_type == "docker":
            sandbox_url = f"http://host.docker.internal:{sandbox_port}"
            self.sandbox_service = SandboxService(
                base_url=sandbox_url,
            )
        elif sandbox_type == "remote":
            sandbox_url = f"http://{sandbox_host}:{sandbox_port}"
            self.sandbox_service = SandboxService(
                base_url=sandbox_url,
            )
        await self.sandbox_service.start()
    
        # 创建上下文管理器
        self.context_manager = ContextManager(
            memory_service=self.memory_service,
            session_history_service=session_history_service
        )
        # 创建环境管理器
        self.environment_manager = EnvironmentManager(
            sandbox_service=self.sandbox_service,
        )

        # 若需要使用沙箱工具
        if self.tools != None:
            sandboxes = self.sandbox_service.connect(
                session_id=session_id,
                user_id=user_id,
                tools=self.tools
            )
            print(f"配置了{len(sandboxes)}个沙箱")

        runer = Runner(
            agent=self.agent,
            context_manager=self.context_manager,
            environment_manager=self.environment_manager,
        )
        self.runner = runer
        self.connected = True

    async def chat(
        self,
        session_id: str,
        user_id: str,
        chat_messages: List[Message],
    ) -> AsyncGenerator[Dict, None]:
        if not self.connected:
            await self.connect(session_id, user_id)

        convert_messages = []
        for chat_message in chat_messages:
            convert_messages.append(
                Message(
                    role=chat_message.role,
                    content=chat_message.content,
                )
            )
        request = AgentRequest(input=convert_messages, session_id=session_id)
        request.tools = []
        async for message in self.runner.stream_query(
            user_id=user_id,
            request=request,
        ):
            if (
                message.object == "message"
                and RunStatus.Completed == message.status
            ):
                yield message.content
    
    async def deploy(
        self,
        host: str = "0.0.0.0",
        port: int = 8001,
        endpoint_path: str = "",
    ) -> None:
        """部署agent

        Args:
            host: 部署的主机IP地址，默认值为 "0.0.0.0"
            port: 部署的端口号，默认值为 8001
            endpoint_path: 部署的端点路径，默认值为空字符串
        """

        if not self.connected:
            raise ValueError("代理未包装为Runner环境, 请先调用 connect 方法。")
        
        def _get_accessible_host(host: str) -> str:
            """获取可访问的主机IP地址。"""
            try:
                if host in ("0.0.0.0", "", None):
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        s.connect(("8.8.8.8", 80))
                        ip = s.getsockname()[0]
                    except Exception:
                        ip = socket.gethostbyname(socket.gethostname())
                        if ip.startswith("127."):
                            ip = "127.0.0.1"
                    finally:
                        s.close()
                    return ip
                return host
            except Exception:
                return "127.0.0.1"

        deploy_manager = LocalDeployManager(
            host=_get_accessible_host(host),
            port=port,
        )
        deploy_result = await self.runner.deploy(
            deploy_manager=deploy_manager,
            endpoint_path=endpoint_path,
            stream=True,
        )

        # print(f"🚀智能体部署在: {deploy_result}")
        # print(f"🌐服务URL: http://{host}:{port}")
        # print(f"💚 健康检查: http://{host}:{port}/health")

        await asyncio.Event().wait()

    async def close(self) -> None:
        """关闭所有服务与沙箱连接。"""
        await self.memory_service.stop()
        await self.sandbox_service.stop()

    def create_exam_question_verification_agent(self) -> AgentScopeAgent:
        """创建考试问题核查智能体。"""

        # 主代理用流式模型，支持异步迭代输出
        if self.llm_binding == "deepseek":
            model = OpenAIChatModel(
                model_name=self.model_name,
                api_key=self.api_key,
                client_args={"base_url": self.base_url},
                stream=True,
            )
            formatter = DeepSeekChatFormatter()
        elif self.llm_binding == "dashscope":
            model = DashScopeChatModel(
                model_name=self.model_name,
                api_key=self.api_key,
                stream=True,
            )
            formatter = DashScopeChatFormatter()
        else:
            raise ValueError(f"不支持的LLM绑定: {self.llm_binding}")

        sys_prompt = PROMPTS["plan_agent_sys_prompt"]

        # from agentscope_runtime.sandbox.tools.base import run_ipython_cell
        # tools = [run_ipython_cell]

        agent = AgentScopeAgent(
            name="Plan_Agent_EQ(V+F)",
            model=model,
            # tools=tools,
            agent_config={
                "sys_prompt": sys_prompt,
                "formatter": formatter,
            },
            agent_builder=ExamQuestionVerificationAgent,
        )
        return agent