import app.core.mail as mail
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import PasswordResetToken, User

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


sent = []


def capture(to, subject, body):
    sent.append({"to": to, "subject": subject, "body": body})
    return True


mail.send_email = capture
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

with Session(engine) as db:
    db.add(
        User(
            email="ada@example.edu",
            username="ada",
            name="Ada Lovelace",
            password_hash=hash_password("Analytical1"),
            role="admin",
        )
    )
    db.add(
        User(
            email="dormant@example.edu",
            username="dormant",
            name="Dormant User",
            password_hash=hash_password("Analytical1"),
            role="student",
            is_active=False,
        )
    )
    db.commit()

unknown = client.post(
    "/api/auth/forgot-password", json={"email": "nobody@example.edu"}
)
assert unknown.status_code == 200, unknown.text
assert sent == [], sent

inactive = client.post(
    "/api/auth/forgot-password", json={"email": "dormant@example.edu"}
)
assert inactive.status_code == 200, inactive.text
assert sent == [], sent
assert inactive.json()["message"] == unknown.json()["message"]

requested = client.post(
    "/api/auth/forgot-password", json={"email": "ADA@example.edu"}
)
assert requested.status_code == 200, requested.text
assert len(sent) == 1, sent

link = [word for word in sent[0]["body"].split() if "reset-password?token=" in word][0]
token = link.split("token=")[1]

with Session(engine) as db:
    stored = db.query(PasswordResetToken).one()
    assert stored.token_hash != token, "raw token must not be stored"

bad = client.post(
    "/api/auth/reset-password",
    json={
        "token": "x" * 32,
        "new_password": "Difference2",
        "confirm_password": "Difference2",
    },
)
assert bad.status_code == 400, bad.text

mismatch = client.post(
    "/api/auth/reset-password",
    json={
        "token": token,
        "new_password": "Difference2",
        "confirm_password": "Difference3",
    },
)
assert mismatch.status_code == 422, mismatch.text

weak = client.post(
    "/api/auth/reset-password",
    json={
        "token": token,
        "new_password": "allletters",
        "confirm_password": "allletters",
    },
)
assert weak.status_code == 422, weak.text

done = client.post(
    "/api/auth/reset-password",
    json={
        "token": token,
        "new_password": "Difference2",
        "confirm_password": "Difference2",
    },
)
assert done.status_code == 200, done.text
admin_token = done.json()["access_token"]

replay = client.post(
    "/api/auth/reset-password",
    json={
        "token": token,
        "new_password": "Another3Pass",
        "confirm_password": "Another3Pass",
    },
)
assert replay.status_code == 400, replay.text

stale = client.post(
    "/api/auth/login", json={"identifier": "ada", "password": "Analytical1"}
)
assert stale.status_code == 401, stale.text

fresh = client.post(
    "/api/auth/login", json={"identifier": "ada", "password": "Difference2"}
)
assert fresh.status_code == 200, fresh.text

client.post("/api/auth/forgot-password", json={"email": "ada@example.edu"})
client.post("/api/auth/forgot-password", json={"email": "ada@example.edu"})
with Session(engine) as db:
    unused = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.used.is_(False))
        .count()
    )
    assert unused == 1, f"only the newest token should stay live, found {unused}"

status_res = client.get(
    "/api/system/status", headers={"Authorization": f"Bearer {admin_token}"}
)
assert status_res.status_code == 200, status_res.text
body = status_res.json()["data"]
assert body["status"] in ("ok", "degraded"), body
names = {c["name"] for c in body["components"]}
assert names == {"database", "storage", "assistant", "mail"}, names
assert body["activity"]["users_total"] == 2, body["activity"]

forbidden = client.get("/api/system/status", headers={"Authorization": "Bearer bad"})
assert forbidden.status_code == 401, forbidden.text

print("password reset and system status: ok")
print(" ", body["status"], sorted(names))
