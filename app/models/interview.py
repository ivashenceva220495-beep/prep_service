# app/models/interview.py
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from app.database import Base
from datetime import datetime


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    session_type = Column(String(50))
    topic = Column(String(100))
    difficulty = Column(String(20))
    questions_asked = Column(JSON, default=list)
    answers_given = Column(JSON, default=list)
    scores = Column(JSON, default=list)
    feedback = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class AnswerHistory(Base):
    __tablename__ = "answer_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    ai_feedback = Column(Text)
    score = Column(Float)
    analyzed_at = Column(DateTime, default=datetime.utcnow)