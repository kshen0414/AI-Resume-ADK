import json
from datetime import datetime
from recruiter_agent.tools.session_utils import SessionStorage

def save_resume_results_to_database(resume_results: dict, user_id: str = "hr_user_001"):
    """
    Save resume processing results to the database.
    
    Args:
        resume_results: Dictionary containing resume analysis results
        user_id: User identifier for the session
    
    Returns:
        Dictionary with save status and session info
    """
    try:
        # Initialize session storage
        storage = SessionStorage()
        
        # Get or create session for user
        session_id, current_data = storage.get_or_create_session(user_id)
        
        # Update session with new results
        updated_data = storage.update_session(session_id, resume_results)
        
        return {
            "status": "success",
            "message": f"✅ Resume saved to database!",
            "session_id": session_id,
            "total_resumes": updated_data['session_stats']['total_resumes'],
            "rating": resume_results.get('rating', 'Unknown')
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"❌ Error saving to database: {str(e)}"
        } 