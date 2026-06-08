"""
app/main.py
FastAPI application exposing the compliance review pipeline.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from app.graph.workflow import get_workflow
from app.services.output_writer import write_outputs
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="Cantordust Nepal Compliance Review API",
    description="AI-powered document intelligence for Nepal solar inverter import compliance.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "model": settings.openai_model}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    pdf1_path: str
    pdf2_path: str
    nepqa_path: str
    output_dir: Optional[str] = "outputs"


class ReviewResponse(BaseModel):
    status: str
    outputs: dict[str, str]
    errors: list[str]
    summary: str


# ---------------------------------------------------------------------------
# Main review endpoint — path-based
# ---------------------------------------------------------------------------

@app.post("/review", response_model=ReviewResponse)
async def run_review(request: ReviewRequest):
    """
    Run the full compliance review pipeline given file paths.
    Paths should be accessible on the server filesystem (e.g. inside /data/).
    """
    for path in [request.pdf1_path, request.pdf2_path, request.nepqa_path]:
        if not os.path.isfile(path):
            raise HTTPException(status_code=400, detail=f"File not found: {path}")

    workflow = get_workflow()
    initial_state = {
        "pdf1_path": request.pdf1_path,
        "pdf2_path": request.pdf2_path,
        "nepqa_path": request.nepqa_path,
        "errors": [],
    }

    try:
        logger.info("Starting compliance review pipeline...")
        final_state = workflow.invoke(initial_state)
        logger.info("Pipeline complete.")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    output_dir = request.output_dir or settings.output_dir
    written = write_outputs(final_state, output_dir)

    reconciliation = final_state.get("reconciliation")
    summary = reconciliation.summary if reconciliation else "Review complete."

    return ReviewResponse(
        status="success",
        outputs=written,
        errors=final_state.get("errors", []),
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Upload endpoint — accepts file uploads directly
# ---------------------------------------------------------------------------

@app.post("/review/upload")
async def run_review_upload(
    pdf1: UploadFile = File(...),
    pdf2: UploadFile = File(...),
    nepqa: UploadFile = File(...),
):
    """
    Upload PDFs directly and run the review pipeline.
    """
    upload_dir = Path(settings.data_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: dict[str, str] = {}
    for key, upload in [("pdf1", pdf1), ("pdf2", pdf2), ("nepqa", nepqa)]:
        dest = upload_dir / upload.filename
        content = await upload.read()
        dest.write_bytes(content)
        saved_paths[key] = str(dest)
        logger.info(f"Saved upload: {dest}")

    workflow = get_workflow()
    initial_state = {
        "pdf1_path": saved_paths["pdf1"],
        "pdf2_path": saved_paths["pdf2"],
        "nepqa_path": saved_paths["nepqa"],
        "errors": [],
    }

    try:
        final_state = workflow.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    output_dir = str(Path(settings.output_dir))
    written = write_outputs(final_state, output_dir)
    reconciliation = final_state.get("reconciliation")
    summary = reconciliation.summary if reconciliation else "Review complete."

    return {
        "status": "success",
        "outputs": written,
        "errors": final_state.get("errors", []),
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Download endpoint
# ---------------------------------------------------------------------------

@app.get("/outputs/{filename}")
def download_output(filename: str):
    path = Path(settings.output_dir) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Output file not found: {filename}")
    return FileResponse(str(path), filename=filename)


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
