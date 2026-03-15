from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.auth import get_current_admin
from app.models.domain import User, ChatSession
from app.schemas.auth import UserResponse
from app.schemas.chat import ChatSessionResponse
from typing import List

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    db: AsyncSession = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(User))
    return result.scalars().all()

@router.get("/chats", response_model=List[ChatSessionResponse])
async def get_all_chats(
    db: AsyncSession = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    # Get all sessions with user info if needed
    result = await db.execute(select(ChatSession).options(selectinload(ChatSession.user)))
    return result.scalars().all()
