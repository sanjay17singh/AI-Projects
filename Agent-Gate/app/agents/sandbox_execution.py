"""Sandbox Execution Agent: runs the Target Support Agent against mocked tools only.

Never touches a real system — every tool is the in-memory mock from
app/agents/target_support/tools.py. Every execution (including its full
transcript and tool calls) is persisted before returning, so nothing here is
lost if the process crashes immediately afterward.
"""

from app.agents.target_support.agent import AgentConfig, execute_scenario
from app.dependencies import AgentDeps
from app.schemas.execution import ChatMessage, RetrievedDocument, ScenarioExecutionResult
from app.schemas.state import AgentGateState
from scenarios.catalog import get_scenario


def run(state: AgentGateState, deps: AgentDeps) -> dict:
    run_id = state["run_id"]
    attempt = state.get("loop_count", 0) + 1
    target_config = state["active_target_config"]

    results: list[ScenarioExecutionResult] = []
    for item in state.get("planned_scenarios", []):
        scenario = get_scenario(item.scenario_id)
        session_customer_id = str(scenario.setup.get("session_customer_id", "CUST-1001"))
        config = AgentConfig(mode=target_config, session_customer_id=session_customer_id)
        input_messages = [ChatMessage(role=m.role, content=m.content) for m in scenario.input_messages]
        retrieved_context = [
            RetrievedDocument(doc_id=d.doc_id, title=d.title, content=d.content, trusted=d.trusted)
            for d in scenario.retrieved_context
        ]

        execution = execute_scenario(
            run_id=run_id,
            scenario_id=scenario.id,
            config=config,
            input_messages=input_messages,
            retrieved_context=retrieved_context,
            attempt=attempt,
            settings=deps.settings,
        )
        results.append(execution)

        with deps.session_factory.session() as session:
            from app.db.repository import record_scenario_execution

            record_scenario_execution(
                session,
                run_id=run_id,
                scenario_id=scenario.id,
                attempt=attempt,
                target_config=target_config,
                status=execution.status,
                transcript=[m.model_dump() for m in execution.transcript],
                tool_calls=[t.model_dump() for t in execution.tool_calls],
                final_output=execution.final_output,
                latency_ms=execution.latency_ms,
                error=execution.error,
            )
            session.commit()

    return {"executions": results}
