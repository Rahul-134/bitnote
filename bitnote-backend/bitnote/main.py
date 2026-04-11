
from fastapi import FastAPI
from bitnote.api.v1.router import api_router
from bitnote.api.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="BitNote Educational AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "BitNote backend is running"}