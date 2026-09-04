from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.api.deps import get_agent_deps
from app.dependencies import AgentDeps

router = APIRouter(tags=["health"])


@router.get("/health")
def health(deps: AgentDeps = Depends(get_agent_deps)):
    checks = {}

    try:
        with deps.session_factory.session() as session:
            session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 - health check must report any failure, not just known ones
        checks["postgres"] = f"unavailable: {exc}"

    checks["pinecone"] = "configured" if deps.settings.pinecone_api_key else "not_configured"
    checks["openai"] = "configured" if deps.settings.openai_api_key else "not_configured"
    checks["langsmith_tracing"] = "enabled" if deps.tracing_callbacks else "disabled"

    overall = "ok" if checks["postgres"] == "ok" else "degraded"
    return {"status": overall, "checks": checks}
