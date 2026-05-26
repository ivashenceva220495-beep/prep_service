# app/models/article.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    user_id = Column(String(100), nullable=False, index=True)
    tags = Column(String(500), default="")
    section = Column(String(100), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи с другими таблицами (используем строковые имена, чтобы избежать циклических импортов)
    code_snippets = relationship(
        "CodeSnippet",
        back_populates="article",
        cascade="all, delete-orphan"
    )
    diagrams = relationship(
        "Diagram",
        back_populates="article",
        cascade="all, delete-orphan"
    )
    images = relationship(
        "Image",
        back_populates="article",
        cascade="all, delete-orphan"
    )