from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from starlette.middleware.sessions import SessionMiddleware
import secrets
import httpx
from urllib.parse import urlencode

from app.config import settings
from app.database import engine, Base
from app.routers import articles, code_snippets, diagrams, images, ai_tutor

# Настройка шаблонов
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    print("Starting up...")
    async with engine.begin() as conn:
        print("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created/verified")
    yield
    print("Shutting down...")
    await engine.dispose()


# Создание приложения
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Добавление CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавление Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

# Подключение роутеров API
app.include_router(articles.router)
app.include_router(code_snippets.router)
app.include_router(diagrams.router)
app.include_router(images.router)
app.include_router(ai_tutor.router)

# Подключение статических файлов
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def get_current_user_from_session(request: Request):
    """Получение текущего пользователя из сессии"""
    return request.session.get("user")


# ========== HTML страницы ==========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница"""
    user = get_current_user_from_session(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/articles", response_class=HTMLResponse)
async def articles_page(request: Request):
    """Страница статей"""
    user = get_current_user_from_session(request)
    if not user:
        return RedirectResponse(url="/login?next=/articles", status_code=302)
    return templates.TemplateResponse("articles.html", {"request": request, "user": user})


@app.get("/codes", response_class=HTMLResponse)
async def codes_page(request: Request):
    """Страница сниппетов кода"""
    user = get_current_user_from_session(request)
    if not user:
        return RedirectResponse(url="/login?next=/codes", status_code=302)
    return templates.TemplateResponse("codes.html", {"request": request, "user": user})


@app.get("/diagrams", response_class=HTMLResponse)
async def diagrams_page(request: Request):
    """Страница диаграмм"""
    user = get_current_user_from_session(request)
    if not user:
        return RedirectResponse(url="/login?next=/diagrams", status_code=302)
    return templates.TemplateResponse("diagrams.html", {"request": request, "user": user})


@app.get("/ai-trainer", response_class=HTMLResponse)
async def ai_trainer_page(request: Request):
    """Страница AI тренажера"""
    user = get_current_user_from_session(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("ai_tutor.html", {"request": request, "user": user})


@app.get("/knowledge-map", response_class=HTMLResponse)
async def knowledge_map_page(request: Request):
    """Страница карты знаний"""
    user = get_current_user_from_session(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("knowledge_map.html", {"request": request, "user": user})


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Страница профиля пользователя"""
    user = get_current_user_from_session(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


# ========== Аутентификация ==========

@app.get("/login")
async def login(request: Request, next: str = "/"):
    """Перенаправление на страницу входа Keycloak"""
    request.session["next_url"] = next

    keycloak_auth_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/auth"

    params = {
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": "http://localhost:8000/auth/callback",
        "scope": "openid profile email",
        "state": secrets.token_urlsafe(32)
    }

    auth_url = f"{keycloak_auth_url}?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Обработка callback от Keycloak после авторизации"""
    if error:
        print(f"OAuth error: {error}")
        return RedirectResponse(url="/", status_code=302)

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")

    try:
        token_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": "http://localhost:8000/auth/callback",
                    "client_id": settings.KEYCLOAK_CLIENT_ID,
                    "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                print(f"Token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Token exchange failed")

            tokens = response.json()
            access_token = tokens.get("access_token")

            userinfo_response = await client.get(
                f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if userinfo_response.status_code != 200:
                print(f"Userinfo failed: {userinfo_response.text}")
                raise HTTPException(status_code=400, detail="Failed to get user info")

            user_info = userinfo_response.json()

            request.session["user"] = user_info
            request.session["access_token"] = access_token

            next_url = request.session.pop("next_url", "/")

            return RedirectResponse(url=next_url, status_code=302)

    except Exception as e:
        print(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@app.get("/logout")
async def logout(request: Request):
    """Выход из системы"""
    request.session.clear()

    logout_url = (
        f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/logout"
        f"?redirect_uri=http://localhost:8000"
    )
    return RedirectResponse(url=logout_url, status_code=302)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG
    )