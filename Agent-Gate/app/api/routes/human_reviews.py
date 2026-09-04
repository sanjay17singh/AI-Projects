from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_agent_deps, get_request_checkpointer
from app.api.schemas import HumanDecisionRequest, HumanDecisionResponse
from app.db.repository import get_review_request, get_run, list_pending_reviews
from app.dependencies import AgentDeps
from app.graph.runner import resume_evaluation

router = APIRouter(tags=["human-reviews"])


def _pending_review(state: dict) -> dict | None:
    interrupts = state.get("__interrupt__")
    if not interrupts:
        return None
    return dict(interrupts[0].value)


@router.get("/human-reviews/pending")
def get_pending_reviews(deps: AgentDeps = Depends(get_agent_deps)):
    with deps.session_factory.session() as session:
        reviews = list_pending_reviews(session)
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "review_type": r.review_type,
                "evidence_ref": r.evidence_ref,
                "available_actions": r.available_actions,
                "created_at": r.created_at,
            }
            for r in reviews
        ]


@router.post("/human-decisions", response_model=HumanDecisionResponse)
def submit_human_decision(
    body: HumanDecisionRequest,
    deps: AgentDeps = Depends(get_agent_deps),
    checkpointer=Depends(get_request_checkpointer),
):
    with deps.session_factory.session() as session:
        review = get_review_request(session, body.review_id)
        if review is None:
            raise HTTPException(status_code=404, detail="review request not found")
        run = get_run(session, review.run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="evaluation run not found")
        thread_id = run.thread_id
        run_id = run.id

    decision_payload = {
        "reviewer": body.reviewer,
        "decision": body.decision,
        "justification": body.justification,
        "idempotency_key": body.idempotency_key or f"{body.review_id}:{body.reviewer}:{body.decision}",
    }
    outcome = resume_evaluation(thread_id, decision_payload, deps, checkpointer)
    pending = _pending_review(outcome["state"])
    return HumanDecisionResponse(
        run_id=run_id,
        status="paused_for_human_review" if pending else outcome["state"].get("workflow_status", "completed"),
        pending_review=pending,
    )
