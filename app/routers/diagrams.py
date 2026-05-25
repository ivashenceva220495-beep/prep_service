from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.diagram import Diagram
from app.schemas.schemas import DiagramCreate, DiagramResponse
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/diagrams", tags=["diagrams"])


def get_user_id_from_session(request: Request):
    """Получение ID пользователя из сессии"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user data")
    return user_id


@router.post("/", response_model=DiagramResponse)
async def create_diagram(
        diagram: DiagramCreate,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """Создание новой диаграммы"""
    user_id = get_user_id_from_session(request)

    db_diagram = Diagram(
        title=diagram.title,
        description=diagram.description,
        diagram_type=diagram.diagram_type,
        content=diagram.content,
        user_id=user_id,
        article_id=diagram.article_id
    )
    db.add(db_diagram)
    await db.commit()
    await db.refresh(db_diagram)
    return db_diagram


@router.get("/", response_model=List[DiagramResponse])
async def get_diagrams(
        request: Request,
        article_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    """Получение списка диаграмм с фильтрацией по статье"""
    user_id = get_user_id_from_session(request)

    query = select(Diagram).where(Diagram.user_id == user_id)

    # Фильтрация по статье
    if article_id:
        query = query.where(Diagram.article_id == article_id)

    query = query.offset(skip).limit(limit).order_by(Diagram.created_at.desc())

    result = await db.execute(query)
    diagrams = result.scalars().all()
    return diagrams


@router.get("/{diagram_id}", response_model=DiagramResponse)
async def get_diagram(
        diagram_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """Получение конкретной диаграммы по ID"""
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(Diagram).where(
            Diagram.id == diagram_id,
            Diagram.user_id == user_id
        )
    )
    diagram = result.scalar_one_or_none()
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram


@router.put("/{diagram_id}", response_model=DiagramResponse)
async def update_diagram(
        diagram_id: int,
        diagram_update: DiagramCreate,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """Обновление существующей диаграммы"""
    user_id = get_user_id_from_session(request)

    # Проверяем существование диаграммы
    result = await db.execute(
        select(Diagram).where(
            Diagram.id == diagram_id,
            Diagram.user_id == user_id
        )
    )
    diagram = result.scalar_one_or_none()
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")

    # Обновляем поля
    diagram.title = diagram_update.title
    diagram.description = diagram_update.description
    diagram.diagram_type = diagram_update.diagram_type
    diagram.content = diagram_update.content
    diagram.article_id = diagram_update.article_id
    diagram.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(diagram)
    return diagram


@router.delete("/{diagram_id}")
async def delete_diagram(
        diagram_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """Удаление диаграммы"""
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        delete(Diagram).where(
            Diagram.id == diagram_id,
            Diagram.user_id == user_id
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Diagram not found")

    await db.commit()
    return {"message": "Diagram deleted successfully"}