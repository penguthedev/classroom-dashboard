from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Department, Faculty, Programme

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
Base.metadata.create_all(engine)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

with Session(engine) as db:
    faculty = Faculty(code="ENG", name="Engineering")
    db.add(faculty)
    db.flush()
    department = Department(faculty_id=faculty.id, code="CS", name="Computer Science")
    db.add(department)
    db.flush()
    programme = Programme(department_id=department.id, code="BCS", name="BSc Computing")
    db.add(programme)
    db.commit()
    programme_id = programme.id

base = {
    "full_name": "Ada Lovelace",
    "username": "ada",
    "email": "ada@example.edu",
    "phone_number": "0123456789",
    "password": "Analytical1",
    "confirm_password": "Analytical1",
    "date_of_birth": "2004-05-01",
    "programme_id": str(programme_id),
    "year_of_study": "2",
}

res = client.post("/api/auth/register/student", data={**base, "id_code": "CS2026001"})
assert res.status_code == 201, res.text
token = res.json()["access_token"]
assert res.json()["user"]["id_code"] == "CS2026001", res.json()

dup = client.post(
    "/api/auth/register/student",
    data={
        **base,
        "id_code": "CS2026001",
        "username": "ada2",
        "email": "ada2@example.edu",
    },
)
assert dup.status_code == 409, dup.text

auto = client.post(
    "/api/auth/register/student",
    data={**base, "username": "grace", "email": "grace@example.edu"},
)
assert auto.status_code == 201, auto.text
generated = auto.json()["user"]["id_code"]
assert generated and generated != "CS2026001", generated

auth = {"Authorization": f"Bearer {token}"}

banner = client.post(
    "/api/uploads/presign",
    json={"kind": "banner", "content_type": "image/png", "filename": "c.png"},
    headers=auth,
)
assert banner.status_code == 403, banner.text

missing_kind = client.post(
    "/api/uploads/presign",
    json={"content_type": "image/png", "filename": "c.png"},
    headers=auth,
)
assert missing_kind.status_code == 422, missing_kind.text

wrong = client.post(
    "/api/auth/change-password",
    json={
        "current_password": "WrongPass1",
        "new_password": "Difference2",
        "confirm_password": "Difference2",
    },
    headers=auth,
)
assert wrong.status_code == 400, wrong.text

mismatch = client.post(
    "/api/auth/change-password",
    json={
        "current_password": "Analytical1",
        "new_password": "Difference2",
        "confirm_password": "Difference3",
    },
    headers=auth,
)
assert mismatch.status_code == 422, mismatch.text

changed = client.post(
    "/api/auth/change-password",
    json={
        "current_password": "Analytical1",
        "new_password": "Difference2",
        "confirm_password": "Difference2",
    },
    headers=auth,
)
assert changed.status_code == 200, changed.text

stale = client.post(
    "/api/auth/login", json={"identifier": "ada", "password": "Analytical1"}
)
assert stale.status_code == 401, stale.text

fresh = client.post(
    "/api/auth/login", json={"identifier": "ada@example.edu", "password": "Difference2"}
)
assert fresh.status_code == 200, fresh.text

for _ in range(5):
    client.post("/api/auth/login", json={"identifier": "ada", "password": "Nope12345"})

locked = client.post(
    "/api/auth/login", json={"identifier": "ada", "password": "Difference2"}
)
assert locked.status_code == 429, locked.text
assert locked.headers.get("Retry-After") == "50", locked.headers
assert locked.json()["detail"]["retry_after_seconds"] == 50, locked.text

print("registration, student id, change-password, lockout, banner gating: ok")
