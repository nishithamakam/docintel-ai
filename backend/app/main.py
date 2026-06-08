from fastapi import FastAPI

app = FastAPI(title="DocIntel AI")

@app.get("/")
def root():
    return {"service": "DocIntel AI", "status": "ok", "message": "Hello from your backend!"}

@app.get("/health")
def health():
    return {"status": "healthy"}
