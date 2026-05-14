from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import attempts, bookmarks, quizzes
from services import storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.ensure_data_dirs()
    yield


app = FastAPI(
    title="Quiz App",
    description="Personal MCQ practice tool",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quizzes.router, prefix="/api")
app.include_router(attempts.router, prefix="/api")
app.include_router(bookmarks.router, prefix="/api")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Quiz App API is running"}
