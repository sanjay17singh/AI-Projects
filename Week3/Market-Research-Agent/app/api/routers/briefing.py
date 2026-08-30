from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.deps import get_db
from app.schemas.briefing import Briefing
from app.services import export_service

router = APIRouter(prefix="/api/v1/briefing", tags=["briefing"])


@router.get("/runs/{run_id}", response_model=Briefing)
def get_briefing(run_id: UUID, db=Depends(get_db)) -> Briefing:
    briefing = export_service.get_briefing(db, run_id)
    if briefing is None:
        raise HTTPException(
            status_code=404, detail="Briefing not found (run may not be complete yet)"
        )
    return briefing


@router.get("/runs/{run_id}/export/markdown")
def export_markdown(run_id: UUID, db=Depends(get_db)) -> Response:
    briefing = export_service.get_briefing(db, run_id)
    if briefing is None:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return Response(
        content=briefing.markdown_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="briefing-{run_id}.md"'},
    )


@router.get("/runs/{run_id}/export/csv")
def export_csv(run_id: UUID, db=Depends(get_db)) -> Response:
    if export_service.get_briefing(db, run_id) is None:
        raise HTTPException(status_code=404, detail="Briefing not found")
    csv_content = export_service.export_csv_bytes(db, run_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="briefing-{run_id}.csv"'},
    )


@router.get("/runs/{run_id}/export/pdf")
def export_pdf(run_id: UUID, db=Depends(get_db)) -> Response:
    if export_service.get_briefing(db, run_id) is None:
        raise HTTPException(status_code=404, detail="Briefing not found")
    pdf_bytes = export_service.export_pdf_bytes(db, run_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="briefing-{run_id}.pdf"'},
    )
