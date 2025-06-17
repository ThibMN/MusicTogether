from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import random
import string
import logging
import time

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
    
    # Créer une nouvelle salle avec l'ID du créateur si disponible
    db_room = RoomModel(
        name=room.name,
        room_code=room_code,
        created_by=room.creator_id  # Utiliser created_by qui correspond au modèle
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    logger.info(f"Salle créée: {room_code}, créateur: {db_room.created_by}")
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
        # Dernier état de lecture pour chaque salle {room_code: {trackId, position, isPlaying, timestamp}}
        self.room_states = {}
    
    async def connect(self, websocket: WebSocket, room_code: str, user_id: int):
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = {}
        self.active_connections[room_code][user_id] = websocket
        logger.info(f"Utilisateur {user_id} connecté à la salle {room_code}. Total: {self.get_users_count(room_code)}")
        
        # Envoyer l'état actuel de la salle au nouvel utilisateur s'il existe
        if room_code in self.room_states:
            state = self.room_states[room_code]
            try:
                logger.info(f"Envoi de l'état actuel à l'utilisateur {user_id}: {state}")
                await websocket.send_json({
                    "type": "playback_state_response",
                    "trackId": state.get("trackId"),
                    "position": state.get("position"),
                    "isPlaying": state.get("isPlaying"),
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'état actuel: {str(e)}")
    
    def disconnect(self, room_code: str, user_id: int):
        if room_code in self.active_connections and user_id in self.active_connections[room_code]:
            del self.active_connections[room_code][user_id]
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]
                # Effacer l'état de la salle si elle est vide
                if room_code in self.room_states:
                    del self.room_states[room_code]
            logger.info(f"Utilisateur {user_id} déconnecté de la salle {room_code}. Total restant: {self.get_users_count(room_code)}")
    
    async def broadcast(self, room_code: str, message: dict):
        if room_code in self.active_connections:
            # Ajouter un timestamp au message
            if "timestamp" not in message:
                message["timestamp"] = time.time()
            
            # Mettre à jour l'état de la salle si c'est un message de contrôle de lecture
            self._update_room_state(room_code, message)
            
            disconnected_users = []
            for user_id, connection in list(self.active_connections[room_code].items()):
                try:
                    # Ne pas renvoyer le message à l'expéditeur pour les messages de contrôle simples
                    if message.get("source_user_id") == user_id and message.get("type") in ["play", "pause", "seek"]:
                        continue
                    
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi du message à l'utilisateur {user_id} dans la salle {room_code}: {str(e)}")
                    # Marquer cet utilisateur comme déconnecté
                    disconnected_users.append(user_id)
            
            # Nettoyer les connexions mortes
            for user_id in disconnected_users:
                self.disconnect(room_code, user_id)
    
    def _update_room_state(self, room_code: str, message: dict):
        """Met à jour l'état de la salle en fonction du message."""
        msg_type = message.get("type")
        
        # Initialiser l'état de la salle si nécessaire
        if room_code not in self.room_states:
            self.room_states[room_code] = {}
        
        # Mise à jour de l'état selon le type de message
        if msg_type in ["play", "pause", "sync", "track_change"]:
            # Mettre à jour l'ID de piste si présent
            if "trackId" in message:
                self.room_states[room_code]["trackId"] = message["trackId"]
            
            # Mettre à jour la position si présente
            if "position" in message:
                self.room_states[room_code]["position"] = message["position"]
            
            # Mettre à jour l'état de lecture si présent
            if "isPlaying" in message:
                self.room_states[room_code]["isPlaying"] = message["isPlaying"]
            elif msg_type == "play":
                self.room_states[room_code]["isPlaying"] = True
            elif msg_type == "pause":
                self.room_states[room_code]["isPlaying"] = False
            
            # Mettre à jour le timestamp
            self.room_states[room_code]["timestamp"] = time.time()
            
            logger.info(f"État de la salle {room_code} mis à jour: {self.room_states[room_code]}")
    
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
        # Établir la connexion
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
                logger.info(f"Message reçu dans la salle {room_code} de l'utilisateur {user_id}: {data}")
                
                # Traiter les messages selon leur type
                msg_type = data.get("type", "")
                
                # Toujours ajouter l'ID de l'expéditeur pour le traçage
                data["source_user_id"] = user_id
                
                if msg_type == "playback_update":
                    # Diffuser la mise à jour de lecture à tous les utilisateurs de la salle
                    logger.info(f"Diffusion mise à jour de lecture: {data}")
                    await manager.broadcast(room_code, data)
                
                elif msg_type in ["play", "pause", "seek", "track_change", "sync"]:
                    # Diffuser les commandes de lecture et synchronisation
                    logger.info(f"Diffusion commande {msg_type}: {data}")
                    # Ajouter timestamp pour calcul de latence côté client
                    data["timestamp"] = time.time()
                    await manager.broadcast(room_code, data)
                
                elif msg_type == "ping":
                    # Répondre au ping pour maintenir la connexion active
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                
                elif msg_type == "request_playback_state":
                    # Rediffuser la demande à tous les clients (un client répondra)
                    logger.info(f"Diffusion demande d'état de lecture pour {data.get('for_user_id')}")
                    await manager.broadcast(room_code, data)
                
                elif msg_type == "playback_state_response":
                    # Transmettre la réponse uniquement au client cible
                    target_user_id = data.get("for_user_id")
                    logger.info(f"Transmission état de lecture à l'utilisateur {target_user_id}")
                    if target_user_id and room_code in manager.active_connections and target_user_id in manager.active_connections[room_code]:
                        try:
                            await manager.active_connections[room_code][target_user_id].send_json(data)
                        except Exception as e:
                            logger.error(f"Erreur lors de l'envoi de l'état de lecture: {str(e)}")
                
                else:
                    logger.warning(f"Type de message inconnu reçu: {msg_type}")
            
            except WebSocketDisconnect:
                logger.info(f"WebSocket déconnecté pour l'utilisateur {user_id} dans la salle {room_code}")
                break
            
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

# Gérer les messages WebSocket
async def handle_websocket_message(data: dict, connection_id: str, websocket: WebSocket, room_code: str, user_id: int):
    # Cas où l'utilisateur envoie un 'ping' pour maintenir la connexion active
    if data.get("type") == "ping":
        logger.info(f"Message reçu dans la salle {room_code} de l'utilisateur {user_id}: {data}")
        await manager.active_connections[room_code][connection_id].send_json({"type": "pong"})
        return
    
    # Cas où l'utilisateur envoie une mise à jour de lecture audio
    if data.get("type") == "playback_update":
        playback_data = {k: v for k, v in data.items() if k != "type"}
        
        # Ajouter l'ID de l'utilisateur source à la mise à jour
        playback_data["source_user_id"] = user_id
        
        # Préserver l'ID client pour identifier la source
        client_id = data.get("client_id")
        if client_id:
            playback_data["client_id"] = client_id
            
        logger.info(f"Message reçu dans la salle {room_code} de l'utilisateur {user_id}: {playback_data}")
        
        # Mettre à jour l'état de la salle (seulement pour les événements sync)
        if playback_data.get("type") == "sync":
            room_state = {
                "trackId": playback_data.get("trackId"),
                "position": playback_data.get("position"),
                "isPlaying": playback_data.get("isPlaying"),
                "timestamp": time.time()
            }
            manager.room_states[room_code] = room_state
            logger.info(f"État de la salle {room_code} mis à jour: {room_state}")
        
        # Diffuser à tous les autres clients connectés
        logger.info(f"Diffusion commande {playback_data.get('type')}: {playback_data}")
        await manager.broadcast(room_code, playback_data)
        return 