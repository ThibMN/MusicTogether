from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional

class ChatMessageBase(BaseModel):
    room_id: int
    message: str

    @validator('message')
    def message_length(cls, v):
        if len(v) > 200:
            raise ValueError('Le message ne peut pas dépasser 200 caractères')
        return v

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessage(ChatMessageBase):
    id: int
    user_id: int
    sent_at: datetime
    
    class Config:
        orm_mode = True

class ChatMessageResponse(ChatMessage):
    username: str 