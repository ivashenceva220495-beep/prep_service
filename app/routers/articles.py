from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.article import Article
from app.models.code_snippet import CodeSnippet
from app.models.diagram import Diagram
from app.schemas.schemas import ArticleCreate, ArticleUpdate, ArticleResponse
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/articles", tags=["articles"])


def get_user_id_from_session(request: Request):
    """Получение ID пользователя из сессии"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user data")
    return user_id


@router.post("/", response_model=ArticleResponse)
async def create_article(
        article: ArticleCreate,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """Создание новой статьи"""
    user_id = get_user_id_from_session(request)

    db_article = Article(
        title=article.title,
        content=article.content,
        tags=article.tags,
        user_id=user_id
    )
    db.add(db_article)
    await db.commit()
    await db.refresh(db_article)
    return db_article


@router.get("/", response_model=List[ArticleResponse])
async def get_articles(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    """Получение списка всех статей пользователя"""
    user_id = get_user_id_from_session(request)

    query = select(Article).where(Article.user_id == user_id)
    query = query.offset(skip).limit(limit).order_by(Article.created_at.desc())

    result = await db.execute(query)
    articles = result.scalars().all()
    return articles


@router.get("/{article_id}")
async def get_article(
        article_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """Получение одной статьи со всеми связанными данными"""
    user_id = get_user_id_from_session(request)

    # Получаем статью
    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == user_id
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Получаем связанные сниппеты кода
    snippets_result = await db.execute(
        select(CodeSnippet).where(CodeSnippet.article_id == article_id)
    )
    snippets = snippets_result.scalars().all()

    # Получаем связанные диаграммы
    diagrams_result = await db.execute(
        select(Diagram).where(Diagram.article_id == article_id)
    )
    diagrams = diagrams_result.scalars().all()

    # Формируем ответ с полными данными
    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "tags": article.tags,
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
    """Обновление существующей статьи"""
    user_id = get_user_id_from_session(request)

    # Находим статью
    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == user_id
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Обновляем только переданные поля
    if article_update.title is not None:
        article.title = article_update.title
    if article_update.content is not None:
        article.content = article_update.content
    if article_update.tags is not None:
        article.tags = article_update.tags

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
    """Удаление статьи (каскадно удаляются связанные сниппеты, диаграммы, изображения)"""
    user_id = get_user_id_from_session(request)

    # Удаляем статью (связанные данные удалятся автоматически благодаря CASCADE)
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