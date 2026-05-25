from keycloak import KeycloakOpenID
from app.config import settings
import httpx
from typing import Optional

from app.schemas.schemas import UserInfo

#интеграция с Keycloak для аутентификации пользователей через OpenID Connect(check jwt token,generate url for open,обмен авторизированного кода на токены)

#создание клиента keycloak
keycloak_openid = KeycloakOpenID(
    server_url=settings.KEYCLOAK_SERVER_URL,
    client_id=settings.KEYCLOAK_CLIENT_ID,
    realm_name=settings.KEYCLOAK_REALM,
    client_secret_key=settings.KEYCLOAK_CLIENT_SECRET
)

#функция аутентификации(проверка токена).Отправляет токен в Keycloak на эндпоинт /userinfo
async def verify_token(token: str) -> Optional[dict]:
    try:
        user_info = keycloak_openid.userinfo(token)
        return user_info
    except Exception as e:
        return None


#Генерирует URL для редиректа пользователя на страницу входа Keycloak. redirect_uri = "http://localhost:8000/auth/callback"
async def get_login_url(redirect_url: str) -> str:
    auth_url = keycloak_openid.auth_url(redirect_uri = redirect_url, scope='openid profile email')
    return auth_url


#Обменивает временный авторизационный код на полноценные токены.
async def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Обмен кода на токены"""
    try:
        token = keycloak_openid.token(
            grant_type="authorization_code",
            code=code,
            redirect_uri=redirect_uri
        )
        print(f"✅ Токены получены от Keycloak")
        return token
    except Exception as e:
        print(f"❌ Ошибка обмена кода: {e}")
        raise


#1. Пользователь → GET /login
#   ↓
#2. FastAPI → get_login_url() → Редирект на Keycloak
#   ↓
#3. Keycloak → Страница входа (пользователь вводит логин/пароль)
#   ↓
#4. Keycloak → Редирект обратно с ?code=abc123
#   ↓
#5. FastAPI → exchange_code_for_token(code) → Получает access_token
#   ↓
#6. FastAPI → Сохраняет токен (cookie/session)
#   ↓
#7. Пользователь → Защищённые API с токеном
#   ↓
#8. FastAPI → verify_token(token) → Получает user_info
