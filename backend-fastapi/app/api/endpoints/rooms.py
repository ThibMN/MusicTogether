from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import random
import string
import logging

from app.db.database import get_db
from app.schemas import Room, RoomCreate, RoomUpdate, RoomDetail, UserCreate
from app.models import Room as RoomModel, User as UserModel

router = APIRouter()
logger = logging.getLogger(__name__)

# Génération de code unique pour les salles
def generate_room_code(length=6):
    """Génère un code aléatoire pour une salle"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@router.post("/", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    """
    Créer une nouvelle salle.
    """
    # Générer un code unique
    room_code = generate_room_code()
    while db.query(RoomModel).filter(RoomModel.room_code == room_code).first():
        room_code = generate_room_code()
    
    # Si un room_code est fourni, l'utiliser
    if room.room_code:
        room_code = room.room_code
    
    db_room = RoomModel(
        name=room.name,
        room_code=room_code
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    logger.info(f"Salle créée: {room_code}")
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
        logger.warning(f"Tentative d'accès à une salle inexistante: {room_code}")
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
        logger.info(f"Utilisateur {user_id} connecté à la salle {room_code}. Total: {self.get_users_count(room_code)}")
    
    def disconnect(self, room_code: str, user_id: int):
        if room_code in self.active_connections and user_id in self.active_connections[room_code]:
            del self.active_connections[room_code][user_id]
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]
            logger.info(f"Utilisateur {user_id} déconnecté de la salle {room_code}. Total restant: {self.get_users_count(room_code)}")
    
    async def broadcast(self, room_code: str, message: dict):
        if room_code in self.active_connections:
            for connection in self.active_connections[room_code].values():
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi du message à un utilisateur dans la salle {room_code}: {str(e)}")
                    # Ne pas lever l'exception pour ne pas interrompre les autres envois
    
    def get_users_count(self, room_code: str) -> int:
        if room_code in self.active_connections:
            return len(self.active_connections[room_code])
        return 0
    
    def is_connected(self, room_code: str, user_id: int) -> bool:
        return (room_code in self.active_connections and 
                user_id in self.active_connections[room_code])

manager = ConnectionManager()

@router.websocket("/ws/{room_code}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_id: int, db: Session = Depends(get_db)):
    """
    WebSocket pour la synchronisation en temps réel des salles.
    """
    logger.info(f"Tentative de connexion WebSocket pour l'utilisateur {user_id} dans la salle {room_code}")
    
    # Vérifier que la salle existe
    db_room = db.query(RoomModel).filter(RoomModel.room_code == room_code).first()
    if db_room is None:
        logger.warning(f"Tentative de connexion WebSocket à une salle inexistante: {room_code}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    try:
        await manager.connect(websocket, room_code, user_id)
        
        # Notifier les autres utilisateurs de la connexion
        await manager.broadcast(room_code, {
            "type": "user_joined",
            "user_id": user_id,
            "users_count": manager.get_users_count(room_code)
        })
        
        # Boucle principale pour recevoir les messages
        while True:
            try:
                data = await websocket.receive_json()
                logger.debug(f"Message reçu dans la salle {room_code} de l'utilisateur {user_id}: {data}")
                
                # Traiter les messages selon leur type
                if data.get("type") == "playback_update":
                    # Diffuser la mise à jour de lecture à tous les utilisateurs de la salle
                    await manager.broadcast(room_code, data)
                elif data.get("type") == "ping":
                    # Répondre au ping pour maintenir la connexion active
                    await websocket.send_json({"type": "pong"})
                else:
                    logger.warning(f"Type de message inconnu reçu: {data.get('type', 'non spécifié')}")
            except Exception as e:
                logger.error(f"Erreur lors du traitement d'un message WebSocket: {str(e)}")
                if not manager.is_connected(room_code, user_id):
                    logger.warning(f"Connexion perdue pour l'utilisateur {user_id} dans la salle {room_code}")
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket déconnecté pour l'utilisateur {user_id} dans la salle {room_code}")
    except Exception as e:
        logger.error(f"Erreur WebSocket non gérée: {str(e)}")
    finally:
        # S'assurer que l'utilisateur est bien déconnecté
        manager.disconnect(room_code, user_id)
        try:
            # Notifier les autres utilisateurs de la déconnexion
            await manager.broadcast(room_code, {
                "type": "user_left",
                "user_id": user_id,
                "users_count": manager.get_users_count(room_code)
            })
        except Exception as e:
            logger.error(f"Erreur lors de la notification de déconnexion: {str(e)}") 