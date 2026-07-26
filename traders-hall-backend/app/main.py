from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import engine

import os

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0", lifespan=lifespan)

frontend_dir = "dist" 
print(os.path.exists(frontend_dir), "HELLOOOOO")

if os.path.exists(frontend_dir):
    app.frontend("/", directory=frontend_dir, fallback="index.html")
else:
    @app.get("/")
    def read_root():
        return {"message": "API is running, but frontend 'dist' is not built yet."}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)