from sqlalchemy import Column, Integer, String, Float, JSON, DateTime,ForeignKey
from app.database import Base
from datetime import datetime


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    topic = Column(String(100), nullable=False)  # 'requirements', 'architecture', 'databases', 'integration'
    subtopic = Column(String(100), nullable=True)
    knowledge_level = Column(Float, default=0.0)  # 0-1
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
    current_streak = Column(Integer, default=0)  # days in a row
    longest_streak = Column(Integer, default=0)
    last_practice_date = Column(DateTime, nullable=True)
    achievements = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KnowledgeNodeLink(Base):
    __tablename__ = "knowledge_node_links"
    id = Column(Integer, primary_key=True)
    from_node_id = Column(Integer, ForeignKey("knowledge_nodes.id"))
    to_node_id = Column(Integer, ForeignKey("knowledge_nodes.id"))
    relation_type = Column(String(50))