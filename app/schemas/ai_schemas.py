from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class StartInterviewRequest(BaseModel):
    position: str

class StartInterviewResponse(BaseModel):
    session_id: str
    message: str

class AnswerRequest(BaseModel):
    session_id: str
    answer: str

class AnswerResponse(BaseModel):
    question_index: int
    total_questions: int
    question: str
    feedback: Dict
    next_question: Optional[str] = None
    is_complete: bool = False

class InterviewFeedback(BaseModel):
    session_id: str
    position: str
    technical_score: int
    soft_skills_score: int
    strengths: List[str]
    improvements: List[str]
    recommendation: str
    detailed_analysis: Dict
    completed_at: datetime

class InterviewHistory(BaseModel):
    session_id: str
    position: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    questions_count: int
    avg_score: Optional[int]