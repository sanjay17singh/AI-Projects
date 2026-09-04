"""The Target Support Agent: vulnerable and guarded configs behind one code path.

The two modes differ only in: identity-boundary enforcement, refund cap
enforcement, and untrusted-content tagging — all inside build_target_tools()
and the system prompt loaded per mode. The tool-calling loop itself is
identical, which is the point: AgentGate is evaluating a configuration
change, not a different program.
"""

import time
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel

from app.agents.prompt_loader import load_prompt
from app.agents.target_support.tools import ToolContext, build_target_tools
from app.config import Settings, get_settings
from app.llm import DEFAULT_TIMEOUT_SECONDS, RETRYABLE_EXCEPTIONS, build_chat_model
from app.schemas.execution import (
    ChatMessage,
    RetrievedDocument,
    ScenarioExecutionResult,
    ToolCallRecord,
)

MAX_TOOL_ITERATIONS = 6


class AgentConfig(BaseModel):
    mode: Literal["vulnerable", "guarded"]
    session_customer_id: str


def _system_prompt(mode: str) -> str:
    return load_prompt(f"target_support_{mode}")


def run_target_support_agent(
    config: AgentConfig,
    input_messages: list[ChatMessage],
    retrieved_context: list[RetrievedDocument],
    settings: Settings | None = None,
) -> tuple[str, list[ChatMessage], list[ToolCallRecord], float, str | None]:
    """Runs the tool-calling loop. Returns (final_output, transcript, tool_calls, latency_ms, error)."""
    settings = settings or get_settings()
    ctx = ToolContext(
        mode=config.mode,
        session_customer_id=config.session_customer_id,
        retrieved_documents=retrieved_context,
    )
    tools = build_target_tools(ctx)
    model = build_chat_model(settings, temperature=0.2, timeout=DEFAULT_TIMEOUT_SECONDS)
    model_with_tools = model.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}

    lc_messages: list = [SystemMessage(content=_system_prompt(config.mode))]
    for m in input_messages:
        if m.role == "system":
            lc_messages.append(SystemMessage(content=m.content))
        else:
            lc_messages.append(HumanMessage(content=m.content))

    transcript: list[ChatMessage] = list(input_messages)
    started = time.perf_counter()
    error: str | None = None
    final_text = ""

    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            response: AIMessage = model_with_tools.invoke(lc_messages)
            lc_messages.append(response)

            if response.content:
                final_text = response.content if isinstance(response.content, str) else str(response.content)

            if not response.tool_calls:
                break

            for tool_call in response.tool_calls:
                tool = tools_by_name.get(tool_call["name"])
                if tool is None:
                    tool_result = f"unknown tool: {tool_call['name']}"
                else:
                    tool_result = tool.invoke(tool_call["args"])
                lc_messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
                )
        else:
            error = "max_tool_iterations_exceeded"
    except RETRYABLE_EXCEPTIONS as exc:
        error = f"openai_infrastructure_failure: {exc}"
    except Exception as exc:  # noqa: BLE001 - captured as scenario execution error, not re-raised
        error = f"target_agent_error: {exc}"

    latency_ms = (time.perf_counter() - started) * 1000
    transcript.append(ChatMessage(role="assistant", content=final_text))
    return final_text, transcript, ctx.call_log, latency_ms, error


def execute_scenario(
    run_id: str,
    scenario_id: str,
    config: AgentConfig,
    input_messages: list[ChatMessage],
    retrieved_context: list[RetrievedDocument],
    attempt: int = 1,
    settings: Settings | None = None,
) -> ScenarioExecutionResult:
    final_text, transcript, tool_calls, latency_ms, error = run_target_support_agent(
        config, input_messages, retrieved_context, settings=settings
    )
    status = "error" if error else "passed"  # "passed" here means "executed cleanly";
    # pass/fail against expectations is decided later by the Policy Evaluation Agent.
    return ScenarioExecutionResult(
        scenario_id=scenario_id,
        run_id=run_id,
        attempt=attempt,
        target_config=config.mode,
        status=status,
        transcript=transcript,
        retrieved_context=retrieved_context,
        tool_calls=tool_calls,
        final_output=final_text,
        latency_ms=latency_ms,
        error=error,
    )
