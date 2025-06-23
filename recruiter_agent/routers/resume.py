from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from google.genai import types
from google.adk.runners import Runner

import os
import json

from recruiter_agent.tools.tools import extract_text_from_uploaded_pdf
from recruiter_agent.agent import (
    APP_NAME,
    USER_ID,
    root_agent,
    session_service,
)

router = APIRouter()


def get_resume_runner(request: Request) -> Runner:
    """FastAPI dependency to get the runner for the resume agent."""
    try:
        return request.app.state.adk.runner_map[root_agent.name]
    except KeyError:
        raise HTTPException(
            status_code=500, detail="Resume filter agent not found or loaded."
        )


@router.post("/rate-resume/")
async def rate_resume_endpoint(
    file: UploadFile = File(..., description="The resume PDF file to be rated."),
    runner: Runner = Depends(get_resume_runner),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a PDF."
        )

    try:
        resume_text = extract_text_from_uploaded_pdf(file)
    except (ImportError, HTTPException) as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not resume_text.strip():
        raise HTTPException(
            status_code=400, detail="Could not extract text from the PDF."
        )

    # Generate unique session ID
    session_id = f"session_{os.urandom(8).hex()}"
    
    # Create session properly (await the coroutine)
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )

    # Set resume_text in session state BEFORE running the agent
    session = session_service.get_session(APP_NAME, USER_ID, session_id)
    session.state["resume_text"] = resume_text

    final_response_content = None
    
    try:
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response_content = event.content.parts[0].text
                break
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Agent failed to process the request: {e}"
        )

    # Retrieve structured results from session state
    session = session_service.get_session(APP_NAME, USER_ID, session_id)
    rating = session.state.get("rating")
    reason = session.state.get("reason")

    return {
        "rating": rating,
        "reason": reason,
        "raw": final_response_content
    }