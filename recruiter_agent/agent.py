import json
from enum import Enum
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent

from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()

from recruiter_agent.tools.tools import (
    rate_resume,
)  # assumes this handles resume file reading

MODEL = "gemini-1.5-flash"

APP_NAME = "resume_filter_app"
USER_ID = "test_hr_user"
SESSION_ID = "session_resume_agent_seq"
MODEL_NAME = "gemini-1.5-flash"


# --- Rating Enum ---
class ResumeRating(str, Enum):
    EXCELLENT = "excellent"
    NORMAL = "normal"
    BAD = "bad"
    FAKE = "fake"


# --- Step 1: Summarization & Flags ---

experience_summary_agent = LlmAgent(
    name="ExperienceSummarizer",
    model=MODEL,
    instruction="""
Extract the candidate's key work experiences in 3–5 bullet points.

Resume:
{+resume_text}+
""",
    output_key="experience_summary",
)

redflag_agent = LlmAgent(
    name="RedFlagDetector",
    model=MODEL,
    instruction="""
Scan the resume text for red flags:
- Buzzwords without substance
- Timeline mismatches
- Vague or suspicious claims

Resume:
{+resume_text}+
""",
    output_key="red_flags",
)

initial_parallel = ParallelAgent(
    name="InitialInsights",
    sub_agents=[experience_summary_agent, redflag_agent],
    description="Summarize experience and detect red flags in parallel",
)


# --- Step 2: Post-Summary Insights ---

seniority_agent = LlmAgent(
    name="SeniorityEstimator",
    model=MODEL,
    instruction="""
Based on the experience summary below, estimate the candidate's seniority level:
Junior, Mid, Senior, or Lead.

Experience Summary:
{+experience_summary}+
""",
    output_key="seniority",
)

salary_agent = LlmAgent(
    name="SalaryEstimator",
    model=MODEL,
    instruction="""
Using the experience summary below, estimate expected monthly salary in their location.

Experience Summary:
{+experience_summary}+
""",
    output_key="expected_salary",
)

culture_fit_agent = LlmAgent(
    name="CultureFitInsight",
    model=MODEL,
    instruction="""
From the experience summary below, assess cultural fit for:
- Fast-paced startups
- Structured corporate teams
- Remote-first environments

Experience Summary:
{+experience_summary}+
""",
    output_key="culture_fit",
)

post_summary_parallel = ParallelAgent(
    name="PostSummaryInsights",
    sub_agents=[seniority_agent, salary_agent, culture_fit_agent],
    description="Estimate seniority, salary, and culture fit based on summary",
)


# --- Step 3: Classification & Explanation ---

classify_agent = LlmAgent(
    name="ResumeClassifier",
    model=MODEL,
    instruction="""
Classify this resume into one of: excellent, normal, bad, or fake.
- excellent: Strong, relevant experience.
- normal: Some relevant experience.
- bad: Little/no relevant experience.
- fake: Suspicious or generic.

Resume:
{+resume_text}+
""",
    output_key="rating",
)

explanation_agent = LlmAgent(
    name="ResumeExplanation",
    model=MODEL,
    instruction="""
Explain why the resume was rated as it was.

Resume:
{+resume_text}+

Rating:
{+rating}+
""",
    output_key="reason",
)

# --- Session Storage Agent ---
session_storage_agent = LlmAgent(
    name="SessionStorageAgent",
    model=MODEL,
    instruction="""
Update the session storage with the resume analysis results.

Current session data:
{+session_data}+

New resume results:
Rating: {+rating}+
Reason: {+reason}+
Seniority: {+seniority}+
Expected Salary: {+expected_salary}+
Experience Summary: {+experience_summary}+
Red Flags: {+red_flags}+
Culture Fit: {+culture_fit}+

Update the processed_resumes list and session_stats counts.
Return the updated session data as JSON.
""",
    output_key="updated_session_data",
)


# --- Root Pipeline ---

root_agent = SequentialAgent(
    name="ResumePipeline",
    sub_agents=[
        # 1) Summarize & flag
        initial_parallel,
        # 2) Insights off the summary
        post_summary_parallel,
        # 3) Final classify + explain
        classify_agent,
        explanation_agent,
        # 4) Update session storage
        session_storage_agent,
    ],
    description=(
        "1) Summarize experience & detect red flags\n"
        "2) Estimate seniority, salary, culture fit from summary\n"
        "3) Classify resume and explain rating\n"
        "4) Update session storage with results"
    ),
)


# --- Session Helper Functions ---


def initialize_session_data():
    """Initialize session data structure for new sessions."""
    return {
        "processed_resumes": [],
        "session_stats": {
            "total_resumes": 0,
            "excellent_count": 0,
            "normal_count": 0,
            "bad_count": 0,
            "fake_count": 0,
        },
    }


def update_session_stats(session_data, rating):
    """Update session statistics based on the new rating."""
    if "session_stats" not in session_data:
        session_data["session_stats"] = {
            "total_resumes": 0,
            "excellent_count": 0,
            "normal_count": 0,
            "bad_count": 0,
            "fake_count": 0,
        }

    session_data["session_stats"]["total_resumes"] += 1

    rating_lower = rating.lower()
    if rating_lower in ["excellent", "normal", "bad", "fake"]:
        session_data["session_stats"][f"{rating_lower}_count"] += 1

    return session_data
