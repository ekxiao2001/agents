import os
import asyncio
import logging

from agentscope_runtime.engine.services.session_history_service import uuid

from src.ExamQuestionVerification.eqv_agent_runtime import EQV_AgentRuntime


# ---------------------------
# Logging
# ---------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------
# load env variables
# ---------------------------
ENV_PATH = os.path.join(os.path.dirname(__file__), "../.env")
if os.path.exists(ENV_PATH):
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)

async def run_agent(agent_runtime: EQV_AgentRuntime):
    try:
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await agent_runtime.connect(
            str(session_id), 
            str(user_id),
            sandbox_type=os.getenv("AGENT_RUNTIME_SANDBOX_TYPE"),
            sandbox_host=os.getenv("AGENT_RUNTIME_SANDBOX_HOST"),
            sandbox_port=int(os.getenv("AGENT_RUNTIME_SANDBOX_PORT")),
        )
        await agent_runtime.deploy(
            host=os.getenv("AGENT_RUNTIME_HOST"),
            port=int(os.getenv("AGENT_RUNTIME_PORT")),
            endpoint_path=os.getenv("AGENT_RUNTIME_ENDPOINT_PATH"),
        )
    except Exception as e:
        logger.error(f"Agent deployment failed: {e}")
        raise e
    except KeyboardInterrupt as e:
        logger.info(f"Agent deployment interrupted by user.")
    finally:
        logger.info("Cleaning up and closing agent...")
        await agent_runtime.close()
        logger.info("Agent deployment finished.")

if __name__ == "__main__":
    agent  = EQV_AgentRuntime(
        llm_binding=os.getenv("LLM_BINDING"),
        model_name=os.getenv("MODEL_NAME"),
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
    )
    asyncio.run(run_agent(agent))

