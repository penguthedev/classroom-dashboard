"""Admin approval + admin-creates-admin checks. Same throwaway in-memory SQLite
setup as the other scripts; run with:  PYTHONPATH=. python tests/check_admin_approvals.py
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Department, Faculty, Programme, StaffProfile, StudentProfile, User

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


@event.listens_for(engine, "connect")
def _fk_on(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


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
    dept = Department(faculty_id=faculty.id, code="CS", name="Computer Science")
    db.add(dept)
    db.flush()
    prog = Programme(department_id=dept.id, code="BCS", name="BSc Computing")
    db.add(prog)
    for username, role in (("root", "admin"), ("tech", "technical")):
        u = User(
            email=f"{username}@uni.edu", username=username, name=username.title(),
            password_hash=hash_password("Password1"), role=role,
            is_active=True, is_approved=True,
        )
        db.add(u)
        db.flush()
        db.add(StaffProfile(user_id=u.id, department_id=dept.id, staff_number=f"S-{username}"))
    db.commit()
    dept_id, prog_id = dept.id, prog.id


def login(identifier, password="Password1"):
    return client.post("/api/auth/login", json={"identifier": identifier, "password": password})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


admin_token = login("root").json()["access_token"]
tech_token = login("tech").json()["access_token"]

common = {
    "phone_number": "0123456789", "password": "Password1", "confirm_password": "Password1",
}

# 1. Student + lecturer register -> pending, cannot log in.
r = client.post("/api/auth/register/student", data={
    **common, "full_name": "Sam Student", "username": "sam", "email": "sam@uni.edu",
    "date_of_birth": "2004-01-01", "programme_id": str(prog_id), "year_of_study": "1",
})
assert r.status_code == 201 and r.json()["pending_approval"] is True, r.text
sam_id = r.json()["user"]["id"]
r = client.post("/api/auth/register/lecturer", data={
    **common, "full_name": "Lee Lecturer", "username": "lee", "email": "lee@uni.edu",
    "date_of_birth": "1980-01-01", "department_id": str(dept_id),
    "academic_position": "lecturer", "specialization": "AI", "qualification": "PhD",
})
assert r.status_code == 201 and r.json()["pending_approval"] is True, r.text
lee_id = r.json()["user"]["id"]
assert login("sam").status_code == 403
assert login("lee").status_code == 403

# 2. Admin sees them in the pending list + count.
r = client.get("/api/users", params={"is_approved": "false"}, headers=auth(admin_token))
assert {u["id"] for u in r.json()["data"]} == {sam_id, lee_id}, r.text
r = client.get("/api/users/pending-count", headers=auth(admin_token))
assert r.json()["data"]["pending"] == 2, r.text

# 3. Non-admins cannot approve / reject / count.
assert client.post(f"/api/users/{sam_id}/approve", headers=auth(tech_token)).status_code == 403
assert client.post(f"/api/users/{sam_id}/reject", headers=auth(tech_token)).status_code == 403
assert client.get("/api/users/pending-count", headers=auth(tech_token)).status_code == 403
assert client.post(f"/api/users/{sam_id}/approve").status_code == 401

# 4. Approve student -> can log in.
r = client.post(f"/api/users/{sam_id}/approve", headers=auth(admin_token))
assert r.status_code == 200 and r.json()["data"]["is_approved"] is True, r.text
assert login("sam").status_code == 200

# 5. Reject lecturer -> account + profile gone, email free again.
assert client.post(f"/api/users/{lee_id}/reject", headers=auth(admin_token)).status_code == 204
with Session(engine) as db:
    assert db.get(User, lee_id) is None
    assert db.scalar(select(StaffProfile).where(StaffProfile.user_id == lee_id)) is None
# Can't reject someone already approved.
assert client.post(f"/api/users/{sam_id}/reject", headers=auth(admin_token)).status_code == 409

# 6. Public admin self-registration is closed.
admin_form = {
    **common, "full_name": "New Admin", "username": "newadmin", "email": "newadmin@uni.edu",
    "department_id": str(dept_id), "position": "Registrar",
}
assert client.post("/api/auth/register/admin", data=admin_form).status_code == 401
assert client.post(
    "/api/auth/register/admin", data=admin_form, headers=auth(tech_token)
).status_code == 403
r = client.post("/api/auth/register/admin", data=admin_form, headers=auth(sam_token := login("sam").json()["access_token"]))
assert r.status_code == 403, r.text

# 7. Admin creates admin -> approved, no token handed back, new admin can log in.
r = client.post("/api/auth/register/admin", data=admin_form, headers=auth(admin_token))
assert r.status_code == 201, r.text
body = r.json()
assert body["access_token"] is None and body["pending_approval"] is False
assert body["user"]["role"] == "admin" and body["user"]["is_approved"] is True
assert login("newadmin").status_code == 200

# 8. Technical services can no longer promote someone to admin.
r = client.patch(f"/api/users/{sam_id}", json={"role": "admin"}, headers=auth(tech_token))
assert r.status_code == 403, r.text
with Session(engine) as db:
    assert db.get(User, sam_id).role == "student"
    assert db.scalar(select(StudentProfile).where(StudentProfile.user_id == sam_id)) is not None

print("admin approval checks passed")
