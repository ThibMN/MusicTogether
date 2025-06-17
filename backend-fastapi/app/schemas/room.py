from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class RoomBase(BaseModel):
    name: str

class RoomCreate(RoomBase):
    room_code: Optional[str] = None
    creator_id: Optional[int] = None

class RoomUpdate(BaseModel):
    name: Optional[str] = None

class Room(RoomBase):
    id: int
    room_code: str
    created_at: datetime
    created_by: Optional[int] = None

    class Config:
        orm_mode = True
        from_attributes = True

class RoomDetail(Room):
    active_users: Optional[int] = 0
    current_track: Optional[dict] = None 