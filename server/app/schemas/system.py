from datetime import datetime

from pydantic import BaseModel


class ComponentStatus(BaseModel):
    name: str
    status: str
    detail: str
    latency_ms: float | None = None


class DatabaseInfo(BaseModel):
    dialect: str
    server_version: str | None = None
    migration_revision: str | None = None
    pool_size: int | None = None
    checked_out: int | None = None


class StorageInfo(BaseModel):
    configured: bool
    endpoint: str | None = None
    bucket: str | None = None
    public_url: str | None = None


class ActivityInfo(BaseModel):
    users_total: int
    users_active: int
    users_locked: int
    failed_logins_pending: int
    schedules_upcoming: int
    notifications_unread: int
    documents_stored: int


class SystemStatusOut(BaseModel):
    status: str
    checked_at: datetime
    api_version: str
    python_version: str
    platform: str
    uptime_seconds: float
    components: list[ComponentStatus]
    database: DatabaseInfo
    storage: StorageInfo
    assistant_enabled: bool
    mail_enabled: bool
    activity: ActivityInfo
