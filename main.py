# main.py
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# Import your existing logic functions
from compliance_checker import check_feature
from database_utils import (
    init_db,
    save_analysis,
    fetch_all_logs,
    update_feedback as db_update_feedback, # Renamed to avoid conflict
    reset_database as db_reset_database
)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="RegTok Compliance API",
    description="API for checking product feature compliance against geo-specific regulations.",
    version="1.0.0"
)

# --- CORS Middleware ---
# This is crucial to allow your Next.js frontend (running on a different port)
# to communicate with this API.
origins = [
    "http://localhost:3000",  # The default Next.js dev server
    # Add your production frontend URL here later
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Data Validation ---
# These models define the structure of the data your API expects in requests.
class AnalysisRequest(BaseModel):
    feature_description: str

class FeedbackRequest(BaseModel):
    log_id: int
    status: str
    corrected_flag: Optional[str] = None
    corrected_reasoning: Optional[str] = None

# --- API Endpoints ---

@app.on_event("startup")
def on_startup():
    """Initialize the database when the API starts."""
    init_db()

@app.post("/analyze", summary="Analyze a feature for compliance")
def analyze_feature(request: AnalysisRequest):
    """
    Receives a feature description, runs the compliance check, saves it,
    and returns the analysis result.
    """
    if not request.feature_description:
        raise HTTPException(status_code=400, detail="Feature description cannot be empty.")
    
    try:
        result = check_feature(request.feature_description)
        # We don't save the analysis here anymore, we just return it.
        # The frontend can decide when/how to save feedback later.
        # However, for the audit log to work, we must save every analysis.
        log_id = save_analysis(result, request.feature_description)
        return {"result": result, "log_id": log_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs", summary="Fetch all analysis logs")
def get_all_logs():
    """Retrieves all historical analysis logs from the database."""
    try:
        log_df = fetch_all_logs()
        # Convert DataFrame to a list of dictionaries for JSON compatibility
        return log_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback", summary="Submit feedback for an analysis")
def update_feedback(request: FeedbackRequest):
    """Updates a log entry with user feedback (approved or corrected)."""
    try:
        db_update_feedback(
            log_id=request.log_id,
            status=request.status,
            corrected_flag=request.corrected_flag,
            corrected_reasoning=request.corrected_reasoning
        )
        return {"message": "Feedback updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/logs", summary="Clear the entire audit history")
def reset_database():
    """Resets the database, clearing all logs."""
    try:
        db_reset_database()
        return {"message": "Database has been successfully reset."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))