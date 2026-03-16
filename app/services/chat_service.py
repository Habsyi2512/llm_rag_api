from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.domain import ChatSession, ChatMessage, User
from app.services.llm_service import get_llm_model
from langchain_core.messages import HumanMessage
import logging

logger = logging.getLogger(__name__)

async def create_chat_session(db: AsyncSession, user_id: int, initial_message: str = None) -> ChatSession:
    title = "New Chat"
    if initial_message:
        try:
            llm = get_llm_model()
            prompt = f"Buatlah judul singkat (maksimal 5 kata) untuk percakapan yang dimulai dengan pesan ini: '{initial_message}'. Berikan hanya judulnya saja tanpa tanda kutip."
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            title = response.content.strip().replace('"', '')
        except Exception as e:
            logger.error(f"Failed to generate chat title: {e}")
            title = initial_message[:30] + "..." if len(initial_message) > 30 else initial_message

    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    await db.commit()
    # await db.refresh(session) # Removed to avoid potential MissingGreenlet issues
    return session

async def save_chat_message(db: AsyncSession, session_id: str, role: str, content: str, retrieved_docs: list = None):
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        retrieved_docs=retrieved_docs
    )
    db.add(message)
    await db.commit()
    return message

async def get_user_sessions(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return result.scalars().all()

async def get_session_messages(db: AsyncSession, session_id: str):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()
