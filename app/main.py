from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

@asynccontextmanager
async def lifespan(app: FastAPI):
  print("App started")
  yield
  print("App stopped")

app = FastAPI(title="Chatbot Layanan Informasi Publik Disdukcapil Kabupaten Kepulauan Anambas", lifespan=lifespan)

@app.post("/chat")
async def chatbot():
  return {
    "message": "hello world"
  }