from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.schemas.music import Music

class PlaylistBase(BaseModel):
    name: str

class PlaylistCreate(PlaylistBase):
    pass

class PlaylistUpdate(BaseModel):
    name: Optional[str] = None

class Playlist(PlaylistBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class PlaylistItemBase(BaseModel):
    playlist_id: int
    music_id: int
    position: int

class PlaylistItemCreate(PlaylistItemBase):
    pass

class PlaylistItemUpdate(BaseModel):
    position: Optional[int] = None

class PlaylistItem(PlaylistItemBase):
    id: int
    added_at: datetime

    class Config:
        orm_mode = True

class PlaylistDetail(Playlist):
    items: List[Music] = []

class FavoriteBase(BaseModel):
    music_id: int

class FavoriteCreate(FavoriteBase):
    pass

class Favorite(FavoriteBase):
    id: int
    user_id: int
    added_at: datetime

    class Config:
        orm_mode = True 