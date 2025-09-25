from fastapi import FastAPI
from auth import router as auth_router

app = FastAPI(title="Digital Loyalty Card API")

# Include auth routes
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
