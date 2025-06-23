import json
import sqlite3
import os
from datetime import datetime

class SessionStorage:
    """Simple session storage using SQLite for resume processing history."""
    
    def __init__(self, db_path="recruiter_sessions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                app_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        """)
        
        # Create resume_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                rating TEXT,
                reason TEXT,
                seniority TEXT,
                expected_salary TEXT,
                experience_summary TEXT,
                red_flags TEXT,
                culture_fit TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_or_create_session(self, user_id, app_name="RecruiterApp"):
        """Get existing session or create a new one."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for existing session
        cursor.execute("""
            SELECT session_id, data FROM sessions 
            WHERE user_id = ? AND app_name = ?
            ORDER BY updated_at DESC LIMIT 1
        """, (user_id, app_name))
        
        result = cursor.fetchone()
        
        if result:
            session_id, data_json = result
            data = json.loads(data_json) if data_json else self._default_session_data()
        else:
            # Create new session
            from uuid import uuid4
            session_id = str(uuid4())
            data = self._default_session_data()
            
            cursor.execute("""
                INSERT INTO sessions (session_id, user_id, app_name, data)
                VALUES (?, ?, ?, ?)
            """, (session_id, user_id, app_name, json.dumps(data)))
            conn.commit()
        
        conn.close()
        return session_id, data
    
    def update_session(self, session_id, resume_results):
        """Update session with new resume processing results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current session data
        cursor.execute("SELECT data FROM sessions WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        
        if result:
            data = json.loads(result[0]) if result[0] else self._default_session_data()
        else:
            data = self._default_session_data()
        
        # Update statistics
        data["session_stats"]["total_resumes"] += 1
        rating = resume_results.get("rating", "").lower()
        if rating in ["excellent", "normal", "bad", "fake"]:
            data["session_stats"][f"{rating}_count"] += 1
        
        # Add to history
        resume_entry = {
            "timestamp": datetime.now().isoformat(),
            "rating": resume_results.get("rating", ""),
            "reason": resume_results.get("reason", ""),
            "seniority": resume_results.get("seniority", ""),
            "expected_salary": resume_results.get("expected_salary", ""),
            "experience_summary": resume_results.get("experience_summary", ""),
            "red_flags": resume_results.get("red_flags", ""),
            "culture_fit": resume_results.get("culture_fit", "")
        }
        data["processed_resumes"].append(resume_entry)
        
        # Update session in database
        cursor.execute("""
            UPDATE sessions 
            SET data = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE session_id = ?
        """, (json.dumps(data), session_id))
        
        # Insert into resume history
        cursor.execute("""
            INSERT INTO resume_history 
            (session_id, rating, reason, seniority, expected_salary, 
             experience_summary, red_flags, culture_fit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            resume_results.get("rating", ""),
            resume_results.get("reason", ""),
            resume_results.get("seniority", ""),
            resume_results.get("expected_salary", ""),
            resume_results.get("experience_summary", ""),
            resume_results.get("red_flags", ""),
            resume_results.get("culture_fit", "")
        ))
        
        conn.commit()
        conn.close()
        
        return data
    
    def get_session_history(self, user_id, app_name="RecruiterApp"):
        """Get session history for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT data FROM sessions 
            WHERE user_id = ? AND app_name = ?
            ORDER BY updated_at DESC LIMIT 1
        """, (user_id, app_name))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        else:
            return {"message": "No session found for this user"}
    
    def _default_session_data(self):
        """Default session data structure."""
        return {
            "processed_resumes": [],
            "session_stats": {
                "total_resumes": 0,
                "excellent_count": 0,
                "normal_count": 0,
                "bad_count": 0,
                "fake_count": 0
            }
        } 