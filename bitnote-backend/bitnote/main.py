# Shree Ganeshay Namah 🙏

import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from bitnote.api.v1.router import api_router
from bitnote.api.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BitNote Educational AI")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5500",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:3000",
]
_env_origins = os.getenv("BITNOTE_CORS_ORIGINS")
CORS_ORIGINS = (
    [origin.strip() for origin in _env_origins.split(",") if origin.strip()]
    if _env_origins
    else DEFAULT_CORS_ORIGINS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "BitNote backend is running"}