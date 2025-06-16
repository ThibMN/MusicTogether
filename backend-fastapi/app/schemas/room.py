from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class RoomBase(BaseModel):
    name: str

class RoomCreate(RoomBase):
    pass

class RoomUpdate(BaseModel):
    name: Optional[str] = None

class Room(RoomBase):
    id: int
    room_code: str
    created_at: datetime
    created_by: int

    class Config:
        orm_mode = True

class RoomDetail(Room):
    active_users: Optional[int] = 0
    current_track: Optional[dict] = None 