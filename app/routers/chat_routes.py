from fastapi import APIRouter, HTTPException, Security
from fastapi.responses import JSONResponse
from app.core.auth import verify_api_key
from app.schemas.requests import ChatRequest
from app.models.state import State
from app.core.startup import get_graph
from app.services.llm_service import get_llm_model
from langchain_core.messages import HumanMessage
from app.utils.prompt_templates import evaluation_norag_prompt
from app.utils.helpers import get_time
import json
import re
import logging

router = APIRouter(prefix="/chat", tags=["Chatbot"])
logger = logging.getLogger(__name__)

@router.post("", include_in_schema=False)
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
        "tracking_data": None,
        "is_eval": request.is_eval
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

@router.post("/no-rag")
async def chatbot_endpoint_no_rag(request: ChatRequest, api_key: str = Security(verify_api_key)):
    try:
        from langchain.schema.output_parser import StrOutputParser
        llm = get_llm_model()

        if request.is_eval:
            current_date = get_time()
            chain = evaluation_norag_prompt | llm | StrOutputParser()
            raw_response = chain.invoke({
                "question": request.message,
                "date": current_date,
                "history": "Belum ada riwayat percakapan."
            })

            # Ekstrak jawaban JSON dari response
            try:
                json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                if json_match:
                    parsed_response = json.loads(json_match.group(0))
                    answer = parsed_response.get("answer", raw_response)
                else:
                    answer = raw_response
            except:
                answer = raw_response

            response_content = answer

        else:
            response = llm.invoke([HumanMessage(content=request.message)])
            response_content = response.content

        return JSONResponse(content={
            "response": response_content,
            "intent": "general",
            "category": "Umum",
            "tracking_data": None
        })
    except Exception as e:
        logger.exception("Chat no-rag error:")
        return JSONResponse(status_code=500, content={"detail": f"Internal processing error: {str(e)}"})


@router.get("/health")
async def health_check():
    return {"status": "ok", "llm_ready": bool(get_graph())}

