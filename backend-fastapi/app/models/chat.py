from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String(200))  # Limite de 200 caractères selon le CDC
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    room = relationship("Room", back_populates="messages")
    user = relationship("User", back_populates="messages") 