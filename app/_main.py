from fastapi import FastAPI, Request, Header, HTTPException
from app.core.config import TELEGRAM_SECRET_TOKEN, BOT_TOKEN
from app.llm_service import graph
import httpx
import os

app = FastAPI()

@app.get("/")
async def root(q: str = None):
    response = graph.invoke({"question": q}) if q else None
    answer = response["answer"] if response else "No question provided"
    print("pertanyaan dari user:", q)
    if not answer:
        answer = "Please provide a question to get an answer."
    return {
        "data": answer, 
        "status": "ok" if q else "no question provided",
        "response": response
        }   

# Endpoint webhook
@app.post("/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    if x_telegram_bot_api_secret_token != TELEGRAM_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    payload = await request.json()
    message = payload.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_message = message.get("text")

    if not user_message:
        return {"status": "no text message"}
    
    if user_message.strip().lower() == "/start":
        welcome_text = (
    "👋 Selamat datang di *Chatbot Layanan Informasi Publik Disdukcapil Kabupaten Kepulauan Anambas!*\n\n"
    "🤖 Saya siap membantu Anda mencari informasi terkait layanan administrasi kependudukan, seperti:\n"
    "🧾 Penerbitan Kartu Keluarga (KK)\n"
    "🪪 KTP Elektronik (KTP-el)\n"
    "🚸 Kartu Identitas Anak (KIA)\n"
    "📄 Akta Kelahiran, Kematian, Perkawinan, dan Perceraian\n"
    "🚚 Surat Keterangan Pindah (SKPWNI)\n"
    "…dan berbagai layanan Disdukcapil lainnya.\n\n"
    "💡 *Cukup ketik pertanyaan Anda*, misalnya:\n"
    "`Bagaimana cara membuat KTP?`\n"
    "`Apa saja syarat membuat Akta Kelahiran?`\n\n"
    "🕘 *Jam Operasional:* Senin – Jumat, 08.00 – 16.00 WIB\n"
    "💰 *Semua layanan GRATIS!* ✅\n\n"
    "Silakan mulai dengan mengetik pertanyaan Anda. Saya siap membantu! 😊"
)


        answer = welcome_text
    else:
        # Gunakan LangGraph untuk menjawab
        result = graph.invoke({"question": user_message})
        answer = result["answer"]


    # Kirim balasan ke Telegram
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": answer
            }
        )
    return {"status": "ok"}


