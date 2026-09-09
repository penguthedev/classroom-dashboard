from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import departments
from app.core.config import settings

app = FastAPI(title="Classroom Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(departments.router, prefix="/api/departments", tags=["departments"])