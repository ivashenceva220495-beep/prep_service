from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.code_snippet import CodeSnippet
from app.schemas.schemas import CodeSnippetCreate, CodeSnippetResponse, FileUploadResponse
from typing import List, Optional
import os
from pathlib import Path
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/code-snippets", tags=["code-snippets"])

# Директория для загруженных файлов
UPLOAD_DIR = Path("uploads/code_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Разрешённые расширения файлов
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.kt', '.sql', '.txt', '.md',
    '.json', '.xml', '.yaml', '.yml', '.sh', '.bat', '.ps1',
    '.html', '.css', '.scss', '.go', '.rs', '.cpp', '.c', '.h',
    '.rb', '.php', '.swift', '.pl', '.pm', '.r', '.scala'
}

def get_user_id_from_session(request: Request):
    """Получение ID пользователя из сессии"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user data")
    return user_id

def get_file_extension(filename: str) -> str:
    """Получение расширения файла"""
    return Path(filename).suffix.lower()

def is_allowed_file(filename: str) -> bool:
    """Проверка разрешённого расширения файла"""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

def get_language_from_extension(filename: str) -> str:
    """Определение языка программирования по расширению файла"""
    ext_to_lang = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.java': 'java', '.kt': 'kotlin', '.sql': 'sql',
        '.json': 'json', '.xml': 'xml', '.yaml': 'yaml',
        '.yml': 'yaml', '.sh': 'bash', '.bat': 'batch',
        '.ps1': 'powershell', '.html': 'html', '.css': 'css',
        '.scss': 'scss', '.go': 'go', '.rs': 'rust',
        '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.rb': 'ruby',
        '.php': 'php', '.swift': 'swift', '.md': 'markdown',
        '.txt': 'text'
    }
    return ext_to_lang.get(get_file_extension(filename), 'text')

@router.post("/upload-file", response_model=FileUploadResponse)
async def upload_code_file(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    article_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Загрузка файла как код-сниппета"""
    user_id = get_user_id_from_session(request)

    # Проверка расширения файла
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    original_filename = file.filename
    file_extension = get_file_extension(original_filename)
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Сохранение файла
    try:
        content = await file.read()
        file_size = len(content)
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Определение языка
    if not language:
        language = get_language_from_extension(original_filename)
    if not title:
        title = original_filename

    # Создание записи в БД
    db_snippet = CodeSnippet(
        title=title,
        code=None,
        language=language,
        description=description or f"Uploaded file: {original_filename}",
        user_id=user_id,
        article_id=article_id,
        filename=original_filename,
        file_path=str(file_path),
        file_size=file_size,
        file_type=file.content_type,
        is_file=True
    )
    db.add(db_snippet)
    await db.commit()
    await db.refresh(db_snippet)

    return FileUploadResponse(
        snippet_id=db_snippet.id,
        filename=original_filename,
        file_size=file_size,
        message="File uploaded successfully"
    )

@router.post("/", response_model=CodeSnippetResponse)
async def create_code_snippet(
    snippet: CodeSnippetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Создание текстового код-сниппета"""
    user_id = get_user_id_from_session(request)

    db_snippet = CodeSnippet(
        title=snippet.title,
        code=snippet.code,
        language=snippet.language,
        description=snippet.description,
        user_id=user_id,
        article_id=snippet.article_id,
        is_file=False
    )
    db.add(db_snippet)
    await db.commit()
    await db.refresh(db_snippet)
    return db_snippet

@router.get("/", response_model=List[CodeSnippetResponse])
async def get_code_snippets(
    request: Request,
    file_type: Optional[str] = None,
    article_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка код-сниппетов с фильтрацией"""
    user_id = get_user_id_from_session(request)

    query = select(CodeSnippet).where(CodeSnippet.user_id == user_id)

    if article_id:
        query = query.where(CodeSnippet.article_id == article_id)
    if file_type == 'file':
        query = query.where(CodeSnippet.is_file == True)
    elif file_type == 'text':
        query = query.where(CodeSnippet.is_file == False)

    query = query.offset(skip).limit(limit).order_by(CodeSnippet.created_at.desc())
    result = await db.execute(query)
    snippets = result.scalars().all()
    return snippets

@router.get("/{snippet_id}", response_model=CodeSnippetResponse)
async def get_code_snippet(
    snippet_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получение конкретного код-сниппета"""
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(CodeSnippet).where(
            CodeSnippet.id == snippet_id,
            CodeSnippet.user_id == user_id
        )
    )
    snippet = result.scalar_one_or_none()
    if not snippet:
        raise HTTPException(status_code=404, detail="Code snippet not found")
    return snippet

@router.get("/{snippet_id}/download")
async def download_code_file(
    snippet_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Скачивание загруженного файла"""
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(CodeSnippet).where(
            CodeSnippet.id == snippet_id,
            CodeSnippet.user_id == user_id
        )
    )
    snippet = result.scalar_one_or_none()
    if not snippet:
        raise HTTPException(status_code=404, detail="Code snippet not found")
    if not snippet.is_file or not snippet.file_path:
        raise HTTPException(status_code=400, detail="This snippet is not a file")

    file_path = Path(snippet.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=file_path,
        filename=snippet.filename,
        media_type=snippet.file_type or "application/octet-stream"
    )

@router.put("/{snippet_id}", response_model=CodeSnippetResponse)
async def update_code_snippet(
    snippet_id: int,
    snippet_update: CodeSnippetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Обновление текстового код-сниппета"""
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(CodeSnippet).where(
            CodeSnippet.id == snippet_id,
            CodeSnippet.user_id == user_id
        )
    )
    snippet = result.scalar_one_or_none()
    if not snippet:
        raise HTTPException(status_code=404, detail="Code snippet not found")
    if snippet.is_file:
        raise HTTPException(status_code=400, detail="Cannot update file-based snippets. Delete and reupload.")

    snippet.title = snippet_update.title
    snippet.code = snippet_update.code
    snippet.language = snippet_update.language
    snippet.description = snippet_update.description
    snippet.article_id = snippet_update.article_id
    snippet.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(snippet)
    return snippet

@router.delete("/{snippet_id}")
async def delete_code_snippet(
    snippet_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Удаление код-сниппета и связанного файла"""
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(CodeSnippet).where(
            CodeSnippet.id == snippet_id,
            CodeSnippet.user_id == user_id
        )
    )
    snippet = result.scalar_one_or_none()
    if not snippet:
        raise HTTPException(status_code=404, detail="Code snippet not found")

    # Удаление физического файла
    if snippet.is_file and snippet.file_path:
        file_path = Path(snippet.file_path)
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete file: {e}")

    await db.delete(snippet)
    await db.commit()
    return {"message": "Code snippet deleted successfully"}