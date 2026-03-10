"""FastAPI application for sprite generation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .routes import actions, avatars, generation
from .storage import DATA_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Sprite Generator API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(avatars.router)
app.include_router(actions.router)
app.include_router(generation.router)

# Serve generated files
app.mount("/api/files", StaticFiles(directory=str(DATA_DIR), check_dir=False), name="files")


@app.get("/api/health")
def health():
    return {"status": "ok"}
