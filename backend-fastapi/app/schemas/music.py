from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MusicBase(BaseModel):
    title: str
    artist: str
    album: Optional[str] = None
    duration: float

class MusicCreate(MusicBase):
    source_url: Optional[str] = None
    file_path: Optional[str] = None

class MusicUpdate(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    cover_path: Optional[str] = None

class Music(MusicBase):
    id: int
    file_path: str
    cover_path: Optional[str] = None
    source_url: Optional[str] = None
    added_at: datetime
    added_by: int

    class Config:
        orm_mode = True

class MusicUpload(BaseModel):
    source_url: str 