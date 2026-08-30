from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter()


@router.get("/healthz")
def healthz(db: Session = Depends(get_db)) -> dict:
    """DB connectivity only — no external (OpenAI/You.com/Pinecone) calls, so
    this works even before any API keys are configured."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "db": f"error: {exc}"}
