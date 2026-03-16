from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.domain import User, ChatSession, ChatMessage
from app.schemas.chat import ChatRequest, ChatSessionResponse, ChatMessageResponse, ChatSessionWithMessages
from app.services.chat_service import create_chat_session, save_chat_message, get_user_sessions, get_session_messages
from app.core.startup import get_graph
from app.models.state import State
from typing import List
import logging

router = APIRouter(prefix="/chat", tags=["Chatbot"])
logger = logging.getLogger(__name__)

@router.post("", response_class=JSONResponse)
@router.post("/", response_class=JSONResponse)
async def chatbot_endpoint(
    request_body: ChatRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    graph = get_graph()
    if not graph:
        raise HTTPException(status_code=503, detail="Service not ready")

    # 1. Handle Session
    session_id = request_body.session_id
    if not session_id:
        session = await create_chat_session(db, current_user.id, request_body.message)
        session_id = session.id
    else:
        # Verify session belongs to user
        session = await db.get(ChatSession, session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")

    # 2. Get history for LangGraph
    history_messages = await get_session_messages(db, session_id)
    langchain_history = []
    for m in history_messages:
        langchain_history.append({"role": m.role, "content": m.content})

    # 3. Save User Message
    await save_chat_message(db, session_id, "user", request_body.message)

    # 4. Invoke RAG Graph
    state: State = {
        "question": request_body.message,
        "context": [],
        "answer": "",
        "conversation_history": langchain_history,
        "user_id": str(current_user.id),
        "intent": "unknown",
        "tracking_number": None,
        "tracking_data": None,
        "category": None,
        "is_eval": False
    }

    try:
        final_state = await graph.ainvoke(state)
        answer = final_state.get("answer", "Maaf, belum bisa menjawab.")
        retrieved_docs = [doc.page_content for doc in final_state.get("context", [])]
        
        # 5. Save Assistant Message
        await save_chat_message(
            db, 
            session_id, 
            "assistant", 
            answer, 
            retrieved_docs=retrieved_docs
        )

        return JSONResponse(content={
            "session_id": session_id,
            "response": answer,
            "intent": final_state.get("intent", "general"),
            "category": final_state.get("category", "Umum"),
            "retrieved_docs": retrieved_docs
        })
    except Exception as e:
        logger.exception("Chat error:")
        return JSONResponse(status_code=500, content={"detail": f"Internal processing error: {str(e)}"})

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_user_sessions(db, current_user.id)

@router.get("/session/{session_id}", response_model=ChatSessionWithMessages)
async def get_session_details(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .options(selectinload(ChatSession.messages))
    )
    session = result.scalars().first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


