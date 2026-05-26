# app/models/knowledge_node.py
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from app.database import Base
from datetime import datetime


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    topic = Column(String(100), nullable=False)
    subtopic = Column(String(100), nullable=True)
    knowledge_level = Column(Float, default=0.0)
    last_practiced = Column(DateTime, nullable=True)
    questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    weak_points = Column(JSON, default=list)
    related_topics = Column(JSON, default=list)


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    total_practice_sessions = Column(Integer, default=0)
    total_questions_answered = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_practice_date = Column(DateTime, nullable=True)
    achievements = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)