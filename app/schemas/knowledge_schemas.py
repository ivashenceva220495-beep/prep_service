from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class KnowledgeNodeCreate(BaseModel):
    title: str
    content: str
    category: str
    difficulty: str = "beginner"
    parent_ids: Optional[List[int]] = []

class KnowledgeNodeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    parent_ids: Optional[List[int]] = None

class KnowledgeNodeResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    difficulty: str
    children: List[int] = []
    parents: List[int] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserProgressUpdate(BaseModel):
    node_id: int
    status: str  # not_started, in_progress, completed, mastered
    mastery_level: int

class UserProgressResponse(BaseModel):
    node_id: int
    status: str
    mastery_level: int
    attempts_count: int
    last_practiced: datetime

    class Config:
        from_attributes = True

class KnowledgeMapResponse(BaseModel):
    nodes: List[KnowledgeNodeResponse]
    edges: List[dict]  # {source: int, target: int}
    user_progress: Dict[int, UserProgressResponse]  # Dict теперь импортирован