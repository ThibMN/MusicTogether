from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Music(Base):
    __tablename__ = "music"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    artist = Column(String(200))
    album = Column(String(200), nullable=True)
    duration = Column(Float)  # en secondes
    file_path = Column(String(500))
    cover_path = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(Integer, ForeignKey("users.id"))
    
    # Relations
    uploader = relationship("User", back_populates="uploaded_music")
    queue_items = relationship("QueueItem", back_populates="music")
    favorites = relationship("Favorite", back_populates="music", cascade="all, delete-orphan")
    playlist_items = relationship("PlaylistItem", back_populates="music", cascade="all, delete-orphan") 