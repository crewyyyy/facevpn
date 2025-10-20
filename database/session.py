import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

load_dotenv()

engine = create_async_engine(url=os.getenv("DB_URL"), echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def async_main():
    """Создает все таблицы"""
    from database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
