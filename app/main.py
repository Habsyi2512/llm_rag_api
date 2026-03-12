# app/main.py
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# # app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.startup import lifespan
from app.routers import chat_routes, vector_routes, dashboard_routes, auth_routes

app = FastAPI(
    title="LLM RAG Disdukcapil Anambas",
    lifespan=lifespan,
    redirect_slashes=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(vector_routes.router)
app.include_router(dashboard_routes.router)

