from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import random
import string

from app.db.database import get_db
from app.schemas import Room, RoomCreate, RoomUpdate, RoomDetail
from app.models import Room as RoomModel

router = APIRouter()

# Génération de code unique pour les salles
def generate_room_code(length=6):
    """Génère un code aléatoire pour une salle"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@router.post("/", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate, user_id: int, db: Session = Depends(get_db)):
    """
    Créer une nouvelle salle.
    """
    # Générer un code unique
    room_code = generate_room_code()
    while db.query(RoomModel).filter(RoomModel.room_code == room_code).first():
        room_code = generate_room_code()
    
    db_room = RoomModel(
        name=room.name,
        room_code=room_code,
        created_by=user_id
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.get("/", response_model=List[Room])
def read_rooms(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupérer la liste des salles.
    """
    rooms = db.query(RoomModel).offset(skip).limit(limit).all()
    return rooms

@router.get("/{room_code}", response_model=RoomDetail)
def read_room(room_code: str, db: Session = Depends(get_db)):
    """
    Récupérer une salle spécifique par son code.
    """
    db_room = db.query(RoomModel).filter(RoomModel.room_code == room_code).first()
    if db_room is None:
        raise HTTPException(status_code=404, detail="Salle non trouvée")
    
    # Ici, on pourrait ajouter des informations supplémentaires comme le nombre d'utilisateurs actifs
    room_detail = RoomDetail.from_orm(db_room)
    # TODO: Ajouter le nombre d'utilisateurs actifs et le morceau en cours
    
    return room_detail

@router.put("/{room_id}", response_model=Room)
def update_room(room_id: int, room: RoomUpdate, db: Session = Depends(get_db)):
    """
    Mettre à jour une salle.
    """
    db_room = db.query(RoomModel).filter(RoomModel.id == room_id).first()
    if db_room is None:
        raise HTTPException(status_code=404, detail="Salle non trouvée")
    
    for key, value in room.dict(exclude_unset=True).items():
        setattr(db_room, key, value)
    
    db.commit()
    db.refresh(db_room)
    return db_room

# Gestionnaire de connexions WebSocket
class ConnectionManager:
    def __init__(self):
        # Dictionnaire {room_code: {user_id: WebSocket}}
        self.active_connections = {}
    
    async def connect(self, websocket: WebSocket, room_code: str, user_id: int):
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = {}
        self.active_connections[room_code][user_id] = websocket
    
    def disconnect(self, room_code: str, user_id: int):
        if room_code in self.active_connections and user_id in self.active_connections[room_code]:
            del self.active_connections[room_code][user_id]
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]
    
    async def broadcast(self, room_code: str, message: dict):
        if room_code in self.active_connections:
            for connection in self.active_connections[room_code].values():
                await connection.send_json(message)
    
    def get_users_count(self, room_code: str) -> int:
        if room_code in self.active_connections:
            return len(self.active_connections[room_code])
        return 0

manager = ConnectionManager()

@router.websocket("/ws/{room_code}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_id: int, db: Session = Depends(get_db)):
    """
    WebSocket pour la synchronisation en temps réel des salles.
    """
    # Vérifier que la salle existe
    db_room = db.query(RoomModel).filter(RoomModel.room_code == room_code).first()
    if db_room is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    await manager.connect(websocket, room_code, user_id)
    
    # Notifier les autres utilisateurs de la connexion
    await manager.broadcast(room_code, {
        "type": "user_joined",
        "user_id": user_id,
        "users_count": manager.get_users_count(room_code)
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            # Traiter les messages selon leur type
            if data["type"] == "playback_update":
                # Diffuser la mise à jour de lecture à tous les utilisateurs de la salle
                await manager.broadcast(room_code, data)
    except WebSocketDisconnect:
        manager.disconnect(room_code, user_id)
        # Notifier les autres utilisateurs de la déconnexion
        await manager.broadcast(room_code, {
            "type": "user_left",
            "user_id": user_id,
            "users_count": manager.get_users_count(room_code)
        }) 