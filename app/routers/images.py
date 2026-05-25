from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.image import Image
from app.schemas.schemas import ImageResponse
from typing import List, Optional
import os
from pathlib import Path
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/images", tags=["images"])

# Создаем директорию для загрузок
UPLOAD_DIR = Path("uploads/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_user_id_from_session(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user.get("sub")


@router.post("/upload", response_model=ImageResponse)
async def upload_image(
        request: Request,
        file: UploadFile = File(...),
        article_id: Optional[int] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    # Генерируем уникальное имя файла
    ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Сохраняем файл
    content = await file.read()
    file_size = len(content)

    with open(file_path, "wb") as f:
        f.write(content)

    # Создаем запись в БД
    image = Image(
        filename=file.filename,
        title=file.filename,
        description=f"Uploaded image: {file.filename}",
        file_path=str(file_path),
        file_size=file_size,
        file_type=file.content_type or "image/jpeg",
        user_id=user_id,
        article_id=article_id
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    return image


@router.get("/", response_model=List[ImageResponse])
async def get_images(
        request: Request,
        article_id: Optional[int] = None,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    query = select(Image).where(Image.user_id == user_id)
    if article_id:
        query = query.where(Image.article_id == article_id)

    query = query.order_by(Image.created_at.desc())
    result = await db.execute(query)
    images = result.scalars().all()
    return images


@router.get("/{image_id}")
async def get_image(
        image_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(Image).where(
            Image.id == image_id,
            Image.user_id == user_id
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Проверяем, существует ли файл
    if not os.path.exists(image.file_path):
        raise HTTPException(status_code=404, detail="Image file not found")

    # Возвращаем файл
    return FileResponse(
        path=image.file_path,
        filename=image.filename,
        media_type=image.file_type
    )


@router.delete("/{image_id}")
async def delete_image(
        image_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(Image).where(
            Image.id == image_id,
            Image.user_id == user_id
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Удаляем физический файл
    if os.path.exists(image.file_path):
        os.remove(image.file_path)

    await db.delete(image)
    await db.commit()
    return {"message": "Image deleted successfully"}