from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.database import get_db
from app.models.article import Article
from app.models.code_snippet import CodeSnippet
from app.models.diagram import Diagram
from app.schemas.schemas import ArticleCreate, ArticleUpdate, ArticleResponse
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/articles", tags=["articles"])


def get_user_id_from_session(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user.get("sub")


@router.post("/", response_model=ArticleResponse)
async def create_article(
        article: ArticleCreate,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    db_article = Article(
        title=article.title,
        content=article.content,
        tags=article.tags or "",
        section=article.section or "general",
        user_id=user_id
    )
    db.add(db_article)
    await db.commit()
    await db.refresh(db_article)
    return db_article


@router.get("/", response_model=List[ArticleResponse])
async def get_articles(
        request: Request,
        section: Optional[str] = Query(None, description="Фильтр по разделу"),
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    query = select(Article).where(Article.user_id == user_id)

    if section:
        query = query.where(Article.section == section)

    query = query.offset(skip).limit(limit).order_by(Article.created_at.desc())

    result = await db.execute(query)
    articles = result.scalars().all()
    return articles


@router.get("/sections")
async def get_sections(
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """Получение списка всех разделов с количеством статей"""
    user_id = get_user_id_from_session(request)

    # Получаем все статьи пользователя с группировкой по разделам
    result = await db.execute(
        select(Article.section, func.count(Article.id).label('count'))
        .where(Article.user_id == user_id)
        .group_by(Article.section)
    )
    rows = result.all()

    # Создаём словарь с количеством статей по разделам
    sections_count = {row.section: row.count for row in rows if row.section}

    # Список всех доступных разделов
    all_sections = [
        {"id": "general", "name": "Общие", "icon": "fas fa-file-alt", "count": sections_count.get("general", 0)},
        {"id": "requirements", "name": "Требования", "icon": "fas fa-clipboard-list",
         "count": sections_count.get("requirements", 0)},
        {"id": "architecture", "name": "Архитектура", "icon": "fas fa-building",
         "count": sections_count.get("architecture", 0)},
        {"id": "databases", "name": "Базы данных", "icon": "fas fa-database",
         "count": sections_count.get("databases", 0)},
        {"id": "integration", "name": "Интеграции", "icon": "fas fa-link",
         "count": sections_count.get("integration", 0)},
        {"id": "security", "name": "Безопасность", "icon": "fas fa-shield-alt",
         "count": sections_count.get("security", 0)},
        {"id": "process", "name": "Процессы", "icon": "fas fa-chart-line", "count": sections_count.get("process", 0)},
        {"id": "interview", "name": "Собеседование", "icon": "fas fa-users",
         "count": sections_count.get("interview", 0)},
    ]

    return all_sections


@router.get("/{article_id}")
async def get_article(
        article_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == user_id
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    snippets_result = await db.execute(
        select(CodeSnippet).where(CodeSnippet.article_id == article_id)
    )
    snippets = snippets_result.scalars().all()

    diagrams_result = await db.execute(
        select(Diagram).where(Diagram.article_id == article_id)
    )
    diagrams = diagrams_result.scalars().all()

    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "tags": article.tags,
        "section": article.section,
        "user_id": article.user_id,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
        "code_snippets": [
            {
                "id": s.id,
                "title": s.title,
                "language": s.language,
                "code": s.code,
                "description": s.description,
                "is_file": s.is_file,
                "filename": s.filename,
                "file_size": s.file_size,
                "created_at": s.created_at
            }
            for s in snippets
        ],
        "diagrams": [
            {
                "id": d.id,
                "title": d.title,
                "diagram_type": d.diagram_type,
                "content": d.content,
                "description": d.description,
                "created_at": d.created_at
            }
            for d in diagrams
        ]
    }


@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
        article_id: int,
        article_update: ArticleUpdate,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == user_id
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article_update.title is not None:
        article.title = article_update.title
    if article_update.content is not None:
        article.content = article_update.content
    if article_update.tags is not None:
        article.tags = article_update.tags
    if article_update.section is not None:
        article.section = article_update.section

    article.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(article)
    return article


@router.delete("/{article_id}")
async def delete_article(
        article_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        delete(Article).where(
            Article.id == article_id,
            Article.user_id == user_id
        )
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Article not found")

    await db.commit()
    return {"message": "Article deleted successfully"}