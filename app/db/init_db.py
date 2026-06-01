from app.db.session import Base, engine

from app.models.user import User


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
