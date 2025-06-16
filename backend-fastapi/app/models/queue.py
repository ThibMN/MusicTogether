from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class QueueItem(Base):
    __tablename__ = "queue_items"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    music_id = Column(Integer, ForeignKey("music.id"))
    added_by = Column(Integer, ForeignKey("users.id"))
    position = Column(Integer)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    room = relationship("Room", back_populates="queue_items")
    music = relationship("Music", back_populates="queue_items")
    user = relationship("User", back_populates="queue_items") 