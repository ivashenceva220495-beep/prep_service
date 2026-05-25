from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ========== Article Schemas ==========
class ArticleBase(BaseModel):
    title: str
    content: str
    tags: Optional[str] = ""


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None


class ArticleResponse(ArticleBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Code Snippet Schemas ==========
class CodeSnippetBase(BaseModel):
    title: str
    language: str
    code: Optional[str] = None
    description: Optional[str] = None
    article_id: Optional[int] = None


class CodeSnippetCreate(CodeSnippetBase):
    pass


class CodeSnippetUpdate(BaseModel):
    title: Optional[str] = None
    language: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    article_id: Optional[int] = None


class CodeSnippetResponse(CodeSnippetBase):
    id: int
    user_id: str
    code: Optional[str] = None  
    filename: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    is_file: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== File Upload Response ==========
class FileUploadResponse(BaseModel):
    snippet_id: int
    filename: str
    file_size: int
    message: str


# ========== Diagram Schemas ==========
class DiagramBase(BaseModel):
    title: str
    diagram_type: str
    content: str
    description: Optional[str] = None
    article_id: Optional[int] = None


class DiagramCreate(DiagramBase):
    pass


class DiagramUpdate(BaseModel):
    title: Optional[str] = None
    diagram_type: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    article_id: Optional[int] = None


class DiagramResponse(DiagramBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== Image Schemas ==========
class ImageBase(BaseModel):
    filename: str
    title: Optional[str] = None
    description: Optional[str] = None
    article_id: Optional[int] = None


class ImageCreate(ImageBase):
    pass


class ImageResponse(ImageBase):
    id: int
    user_id: str
    file_path: str
    file_size: int
    file_type: str
    created_at: datetime

    class Config:
        from_attributes = True


# ========== AI Tutor Schemas ==========
class QuestionRequest(BaseModel):
    topic: str
    difficulty: str = "middle"


class AnswerRequest(BaseModel):
    session_id: int
    answer: str


class AnalysisResponse(BaseModel):
    scores: dict
    strengths: List[str]
    improvements: List[str]
    missing_points: List[str]
    overall_score: int
    improved_answer: str
    next_question_topic: str


class SessionResponse(BaseModel):
    session_id: int
    question: str
    topic: str
    difficulty: str


# ========== User Schemas ==========
class UserInfo(BaseModel):
    sub: str
    email: str
    preferred_username: str
    name: Optional[str] = None