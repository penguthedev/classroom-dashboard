from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    assistant,
    auth,
    buildings,
    classes,
    departments,
    documents,
    enrollments,
    faculties,
    meta,
    notifications,
    programmes,
    rooms,
    schedules,
    stats,
    subjects,
    system,
    uploads,
    users,
)
from app.core.config import settings

app = FastAPI(title="Classroom Dashboard API", version="0.2.0")

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


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(faculties.router, prefix="/api/faculties", tags=["faculties"])
app.include_router(departments.router, prefix="/api/departments", tags=["departments"])
app.include_router(programmes.router, prefix="/api/programmes", tags=["programmes"])
app.include_router(subjects.router, prefix="/api/subjects", tags=["subjects"])
app.include_router(classes.router, prefix="/api/classes", tags=["classes"])
app.include_router(enrollments.router, prefix="/api/enrollments", tags=["enrollments"])
app.include_router(buildings.router, prefix="/api/buildings", tags=["buildings"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(schedules.router, prefix="/api/schedules", tags=["schedules"])
app.include_router(
    notifications.router, prefix="/api/notifications", tags=["notifications"]
)
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(meta.router, prefix="/api/meta", tags=["meta"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["assistant"])
