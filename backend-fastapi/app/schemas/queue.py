from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.schemas.music import Music

class QueueItemBase(BaseModel):
    room_id: int
    music_id: int
    position: int

class QueueItemCreate(QueueItemBase):
    pass

class QueueItemUpdate(BaseModel):
    position: int

class QueueItem(QueueItemBase):
    id: int
    added_by: int
    added_at: datetime

    class Config:
        orm_mode = True

class QueueItemDetail(QueueItem):
    music: Music 