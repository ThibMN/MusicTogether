from fastapi import APIRouter

router = APIRouter()

# Importer les sous-routers
from app.api.endpoints import users, rooms, music, queue, chat, playlists

# Inclure les sous-routers
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
router.include_router(music.router, prefix="/music", tags=["music"])
router.include_router(queue.router, prefix="/queue", tags=["queue"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(playlists.router, prefix="/playlists", tags=["playlists"])

@router.get("/ping")
def ping():
    return {"message": "pong"}