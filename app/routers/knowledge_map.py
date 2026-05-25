from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.database import get_db
from app.models.knowledge_node import KnowledgeNode, UserProgress, KnowledgeNodeLink
from app.schemas.knowledge_schemas import *
from app.dependencies import get_current_user
from app.schemas.schemas import UserInfo
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/knowledge", tags=["knowledge-map"])


@router.get("/nodes", response_model=List[KnowledgeNodeResponse])
async def get_all_nodes(
        category: str = None,
        db: AsyncSession = Depends(get_db),
        current_user: UserInfo = Depends(get_current_user)
):
    """Получить все узлы карты знаний"""

    query = select(KnowledgeNode).where(KnowledgeNode.user_id == current_user.sub)
    if category:
        query = query.where(KnowledgeNode.category == category)

    result = await db.execute(query.order_by(KnowledgeNode.order_index))
    nodes = result.scalars().all()

    response_nodes = []
    for node in nodes:
        # Явно загружаем связи для каждого узла
        await db.refresh(node, ['children', 'parents'])

        response_nodes.append({
            "id": node.id,
            "title": node.title,
            "content": node.content,
            "category": node.category,
            "difficulty": node.difficulty,
            "children": [child.id for child in node.children],
            "parents": [parent.id for parent in node.parents],
            "created_at": node.created_at,
            "updated_at": node.updated_at
        })

    return response_nodes


@router.get("/map", response_model=KnowledgeMapResponse)
async def get_knowledge_map(
        category: str = None,
        db: AsyncSession = Depends(get_db),
        current_user: UserInfo = Depends(get_current_user)
):
    """Получить полную карту знаний с прогрессом пользователя"""

    query = select(KnowledgeNode).where(KnowledgeNode.user_id == current_user.sub)
    if category:
        query = query.where(KnowledgeNode.category == category)

    result = await db.execute(query.order_by(KnowledgeNode.order_index))
    nodes = result.scalars().all()

    # Формируем узлы
    node_list = []
    edges = []

    for node in nodes:
        # Явно загружаем связи
        await db.refresh(node, ['children', 'parents'])

        node_list.append({
            "id": node.id,
            "title": node.title,
            "content": node.content,
            "category": node.category,
            "difficulty": node.difficulty,
            "children": [child.id for child in node.children],
            "parents": [parent.id for parent in node.parents],
            "created_at": node.created_at,
            "updated_at": node.updated_at
        })

        # Добавляем связи для графа
        for child in node.children:
            edges.append({"source": node.id, "target": child.id})

    # Получаем прогресс пользователя
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.sub
        )
    )
    progress_records = result.scalars().all()

    user_progress = {
        p.node_id: {
            "node_id": p.node_id,
            "status": p.status,
            "mastery_level": p.mastery_level,
            "attempts_count": p.attempts_count,
            "last_practiced": p.last_practiced
        }
        for p in progress_records
    }

    return {
        "nodes": node_list,
        "edges": edges,
        "user_progress": user_progress
    }

@router.post("/nodes", response_model=KnowledgeNodeResponse)
async def create_node(
        node_data: KnowledgeNodeCreate,
        db: AsyncSession = Depends(get_db),
        current_user: UserInfo = Depends(get_current_user)
):
    """Создать новый узел знаний"""

    db_node = KnowledgeNode(
        title=node_data.title,
        content=node_data.content,
        category=node_data.category,
        difficulty=node_data.difficulty,
        user_id=current_user.sub
    )

    db.add(db_node)
    await db.commit()
    await db.refresh(db_node)

    # Добавляем связи с родителями
    if node_data.parent_ids:
        for parent_id in node_data.parent_ids:
            # Явно загружаем родителя в текущую сессию
            result = await db.execute(
                select(KnowledgeNode).where(KnowledgeNode.id == parent_id)
            )
            parent = result.scalar_one_or_none()
            if parent:
                # Используем await для загрузки отношения
                await db.refresh(parent, ['children'])
                db_node.parents.append(parent)

        await db.commit()
        await db.refresh(db_node)

    # Явно загружаем связи перед возвратом ответа
    # Это важно, чтобы избежать MissingGreenlet ошибки
    await db.refresh(db_node, ['children', 'parents'])

    # Собираем ID детей и родителей
    children_ids = []
    for child in db_node.children:
        children_ids.append(child.id)

    parents_ids = []
    for parent in db_node.parents:
        parents_ids.append(parent.id)

    return {
        "id": db_node.id,
        "title": db_node.title,
        "content": db_node.content,
        "category": db_node.category,
        "difficulty": db_node.difficulty,
        "children": children_ids,
        "parents": parents_ids,
        "created_at": db_node.created_at,
        "updated_at": db_node.updated_at
    }

@router.put("/nodes/{node_id}", response_model=KnowledgeNodeResponse)
async def update_node(
        node_id: int,
        node_data: KnowledgeNodeUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: UserInfo = Depends(get_current_user)
):
    """Обновить узел знаний"""

    result = await db.execute(
        select(KnowledgeNode).where(
            KnowledgeNode.id == node_id,
            KnowledgeNode.user_id == current_user.sub
        )
    )
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node_data.title is not None:
        node.title = node_data.title
    if node_data.content is not None:
        node.content = node_data.content
    if node_data.category is not None:
        node.category = node_data.category
    if node_data.difficulty is not None:
        node.difficulty = node_data.difficulty

    node.updated_at = datetime.utcnow()

    # Обновляем связи
    if node_data.parent_ids is not None:
        # Очищаем текущие связи
        node.parents = []
        await db.commit()

        # Добавляем новые
        for parent_id in node_data.parent_ids:
            parent_result = await db.execute(
                select(KnowledgeNode).where(KnowledgeNode.id == parent_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent:
                node.parents.append(parent)

    await db.commit()
    await db.refresh(node)

    return {
        "id": node.id,
        "title": node.title,
        "content": node.content,
        "category": node.category,
        "difficulty": node.difficulty,
        "children": [child.id for child in node.children],
        "parents": [parent.id for parent in node.parents],
        "created_at": node.created_at,
        "updated_at": node.updated_at
    }


@router.delete("/nodes/{node_id}")
async def delete_node(
        node_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserInfo = Depends(get_current_user)
):
    """Удалить узел знаний"""

    result = await db.execute(
        select(KnowledgeNode).where(
            KnowledgeNode.id == node_id,
            KnowledgeNode.user_id == current_user.sub
        )
    )
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    await db.delete(node)
    await db.commit()

    return {"message": "Node deleted"}


@router.post("/progress")
async def update_progress(
        progress_data: UserProgressUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: UserInfo = Depends(get_current_user)
):
    """Обновить прогресс пользователя по узлу знаний"""

    # Проверяем существование узла
    result = await db.execute(
        select(KnowledgeNode).where(KnowledgeNode.id == progress_data.node_id)
    )
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Обновляем или создаем запись прогресса
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.sub,
            UserProgress.node_id == progress_data.node_id
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        progress.status = progress_data.status
        progress.mastery_level = progress_data.mastery_level
        progress.attempts_count += 1
        progress.last_practiced = datetime.utcnow()
    else:
        progress = UserProgress(
            user_id=current_user.sub,
            node_id=progress_data.node_id,
            status=progress_data.status,
            mastery_level=progress_data.mastery_level,
            attempts_count=1
        )
        db.add(progress)

    await db.commit()

    return {"message": "Progress updated"}


@router.get("/progress", response_model=List[UserProgressResponse])
async def get_user_progress(
        db: AsyncSession = Depends(get_db),
        current_user: UserInfo = Depends(get_current_user)
):
    """Получить прогресс пользователя по всем узлам"""

    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == current_user.sub
        )
    )
    progress_records = result.scalars().all()

    return [
        {
            "node_id": p.node_id,
            "status": p.status,
            "mastery_level": p.mastery_level,
            "attempts_count": p.attempts_count,
            "last_practiced": p.last_practiced
        }
        for p in progress_records
    ]