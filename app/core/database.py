import contextlib
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import select, text
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Create async engine
# For MySQL, we use pool_size and max_overflow
# For SQLite, we need check_same_thread=False
is_sqlite = "sqlite" in settings.DATABASE_URL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=(
        {"check_same_thread": False} if is_sqlite 
        else {"init_command": "SET time_zone='+07:00'"}
    ),
    # MySQL specific pooling
    **({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600,
    } if not is_sqlite else {})
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def init_db() -> None:
    """Initialize database tables and seed initial data."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed admin user
    from app.models.domain import User
    from app.core.security import get_password_hash
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        admin = result.scalars().first()
        
        if not admin:
            new_admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin"
            )
            session.add(new_admin)
            await session.commit()
            print(f"✅ Admin user created: {settings.ADMIN_EMAIL}")

async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
