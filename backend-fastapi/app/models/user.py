from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relations
    created_rooms = relationship("Room", back_populates="creator")
    uploaded_music = relationship("Music", back_populates="uploader")
    queue_items = relationship("QueueItem", back_populates="user")
    messages = relationship("ChatMessage", back_populates="user")
    playlists = relationship("Playlist", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")