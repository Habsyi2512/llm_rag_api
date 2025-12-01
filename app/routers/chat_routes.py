from fastapi import APIRouter, HTTPException, Security
from fastapi.responses import JSONResponse
from app.core.auth import verify_api_key
from app.schemas.requests import ChatRequest
from app.models.state import State
from app.core.startup import get_graph
import logging

router = APIRouter(prefix="/chat", tags=["Chatbot"])
logger = logging.getLogger(__name__)

@router.post("/")
async def chatbot_endpoint(request: ChatRequest, api_key: str = Security(verify_api_key)):
    graph = get_graph()
    if not graph:
        raise HTTPException(status_code=503, detail="Service not ready")

    state: State = {
        "question": request.message,
        "context": [],
        "answer": "",
        "conversation_history": request.history or [],
        "user_id": request.user_id or "anonymous",
        "intent": "unknown",
        "tracking_number": None,
        "tracking_data": None
    }

    try:
        final_state = await graph.ainvoke(state)
        tracking_data = final_state.get("tracking_data")

        # pastikan tracking_data aman di-serialize
        import json
        try:
            json.dumps(tracking_data, ensure_ascii=False)
        except Exception:
            tracking_data = str(tracking_data)

        return JSONResponse(content={
            "response": final_state.get("answer", "Maaf, belum bisa menjawab."),
            "intent": final_state.get("intent", "general"),
            "category": final_state.get("category", "Umum"),
            "tracking_data": tracking_data
        })
    except Exception as e:
        logger.exception("Chat error:")
        return JSONResponse(status_code=500, content={"detail": f"Internal processing error: {str(e)}"})


@router.get("/health")
async def health_check():
    return {"status": "ok", "llm_ready": bool(get_graph())}

