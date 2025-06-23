import json
import os
import logging
from io import BytesIO
from fastapi import UploadFile, HTTPException

from google.genai import types

from recruiter_agent.tools.utils import extract_text_from_pdf
from .utils import extract_text_from_pdf, extract_text_from_uploaded_pdf

async def rate_resume(
    runner_instance, agent_instance, resume_file_path: str, session_service
):
    """
    Extracts text from a resume and submits it to a SequentialAgent for classification + explanation.
    Prints both raw and structured responses.
    """
    print(f"\n>>> Processing resume: '{resume_file_path}'")
    resume_text = extract_text_from_pdf(resume_file_path)

    if not resume_text or "Error reading PDF" in resume_text:
        print("❌ Resume text is invalid. Skipping agent call.")
        return

    # Create session properly (await the coroutine)
    user_id = "test_hr_user"
    session_id = "session_resume_agent_xyz"
    await session_service.create_session(
        app_name="resume_filter_app", user_id=user_id, session_id=session_id
    )

    # Set resume_text in session state before running
    session = session_service.get_session("resume_filter_app", user_id, session_id)
    session.state["resume_text"] = resume_text

    print("\n>>> Running agent with resume text in state...")
    async for event in runner_instance.run_async(
        user_id=user_id,
        session_id=session_id,
    ):
        if event.is_final_response():
            print("\n<<< Final response event received.")
            break

    # Retrieve results from session state
    state = session_service.get_state(
        app_name="resume_filter_app", user_id=user_id, session_id=session_id
    )

    rating = state.get("rating")
    reason = state.get("reason")

    print("\n--- Parsed Agent Output ---")
    print(json.dumps({"rating": rating, "reason": reason}, indent=2))
    print("-" * 40)