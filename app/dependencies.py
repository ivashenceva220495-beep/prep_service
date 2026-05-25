from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.auth import verify_token
from app.schemas.schemas import UserInfo

security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserInfo]:
    """Получение текущего пользователя (опционально) - для HTML страниц"""

    # Сначала пробуем получить токен из заголовка Authorization
    token = None
    if credentials:
        token = credentials.credentials

    # Если нет в заголовках, пробуем взять из cookie
    if not token:
        token = request.cookies.get("access_token")
        if token:
            print(f"🔍 Токен взят из cookie для HTML страницы")

    if not token:
        return None

    user_info = await verify_token(token)
    if not user_info:
        print(f"🔍 Токен не валиден")
        return None

    print(f"🔍 Пользователь аутентифицирован: {user_info.get('preferred_username')}")
    return UserInfo(
        sub=user_info.get("sub"),
        email=user_info.get("email", ""),
        preferred_name=user_info.get("preferred_username", ""),
        name=user_info.get("name")
    )


async def get_current_user(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserInfo:
    """Получение текущего пользователя (обязательно) - для API эндпоинтов"""

    # Сначала пробуем получить токен из заголовка Authorization
    token = None
    if credentials:
        token = credentials.credentials

    # Если нет в заголовках, пробуем взять из cookie
    if not token:
        token = request.cookies.get("access_token")
        if token:
            print(f"🔍 Токен взят из cookie для API")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = await verify_token(token)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    print(f"🔍 API запрос от пользователя: {user_info.get('preferred_username')}")
    return UserInfo(
        sub=user_info.get("sub"),
        email=user_info.get("email", ""),
        preferred_name=user_info.get("preferred_username", ""),
        name=user_info.get("name")
    )