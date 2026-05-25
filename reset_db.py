import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings
from app.database import Base

async def reset_database():
    print(f"Подключение к БД: {settings.DATABASE_URL}")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # Каскадно удаляем всю схему public
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        print("Схема public пересоздана.")

        # Создаём таблицы по новым моделям
        await conn.run_sync(Base.metadata.create_all)
        print("Таблицы созданы.")

    await engine.dispose()
    print("Сброс завершён.")

if __name__ == "__main__":
    asyncio.run(reset_database())