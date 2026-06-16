"""
DocIntel AI - Main FastAPI Application

This is the entry point of the backend.
It creates the app and registers all route handlers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.upload import router as upload_router

# Create the FastAPI application
app = FastAPI(
    title="DocIntel AI",
    description="Enterprise Document Intelligence & RAG System",
    version="1.0.0",
)

# ── CORS Middleware ─────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# This allows our React frontend (running on port 5173)
# to make requests to our backend (running on port 8000)
# Without this, browsers block cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternative React port
    ],
    allow_credentials=True,
    allow_methods=["*"],           # Allow all HTTP methods
    allow_headers=["*"],           # Allow all headers
)

# ── Register Routers ────────────────────────────────────────
# Each router handles a group of related endpoints
app.include_router(upload_router, prefix="/api", tags=["Documents"])

# ── Health Check ────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "service": "DocIntel AI",
        "status": "ok",
        "version": "1.0.0",
        "message": "Welcome to DocIntel AI API"
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
