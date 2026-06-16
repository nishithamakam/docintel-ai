"""
DocIntel AI - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.upload import router as upload_router
from app.api.chat import router as chat_router      # ← NEW

app = FastAPI(
    title="DocIntel AI",
    description="Enterprise Document Intelligence & RAG System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ─────────────────────────────────────────
app.include_router(upload_router, prefix="/api", tags=["Documents"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])    # ← NEW

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "DocIntel AI",
        "status": "ok",
        "version": "1.0.0",
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
