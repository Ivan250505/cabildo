from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class DriveAuthUrlResponse(BaseModel):
    url: str
    state: str


class DriveStatusResponse(BaseModel):
    connected: bool
    google_email: str | None = None


class DriveFileInfo(BaseModel):
    id: str
    name: str
    mime_type: str
    size_bytes: int | None
    modified_at: datetime | None
    web_view_link: str | None


class FolderListResponse(BaseModel):
    folder_id: str
    total: int
    items: list[DriveFileInfo]


class SyncResult(BaseModel):
    study_id: UUID
    fase: str
    files_found: int
    files_downloaded: int
    files_skipped: int
    errors: list[str]


class StudySyncResponse(BaseModel):
    study_id: UUID
    fases: list[SyncResult]
    total_downloaded: int
    total_errors: int
