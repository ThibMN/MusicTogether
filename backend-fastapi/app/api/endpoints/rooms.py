from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import random
import string
import logging
import time
import json
from datetime import datetime

from app.db.database import get_db
from app.schemas import Room, RoomCreate, RoomUpdate, RoomDetail, UserCreate
from app.models import Room as RoomModel, User as UserModel, QueueItem as QueueItemModel, Music as MusicModel

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
    
    # Récupérer le nombre d'utilisateurs connectés
    users_count = manager.get_users_count(room_code)
    
    # Récupérer la piste en cours de lecture si elle existe
    current_track = None
    if room_code in manager.room_states and 'trackId' in manager.room_states[room_code]:
        track_id = manager.room_states[room_code]['trackId']
        if track_id:
            track = db.query(MusicModel).filter(MusicModel.id == track_id).first()
            if track:
                current_track = {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist,
                    "cover_path": track.cover_path
                }
    
    # Créer l'objet de détail de la salle
    room_detail = RoomDetail.from_orm(db_room)
    room_detail.active_users = users_count
    room_detail.current_track = current_track
    
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
        # File d'attente pour chaque salle {room_code: [queue_items]}
        self.room_queues = {}
    
    async def connect(self, websocket: WebSocket, room_code: str, user_id: int, db: Session = None):
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = {}
        self.active_connections[room_code][user_id] = websocket
        logger.info(f"Utilisateur {user_id} connecté à la salle {room_code}. Total: {self.get_users_count(room_code)}")
        
        # Charger l'état actuel de la salle au premier utilisateur qui se connecte
        if db and room_code not in self.room_states:
            self._load_room_state(room_code, db)
        
        # Envoyer l'état actuel de la salle au nouvel utilisateur s'il existe
        if room_code in self.room_states:
            state = self.room_states[room_code]
            try:
                # Générer un ID client côté serveur pour ce message
                client_id = f"server_{int(time.time())}"
                
                logger.info(f"Envoi de l'état actuel à l'utilisateur {user_id}: {state}")
                await websocket.send_json({
                    "type": "playback_state_response",
                    "trackId": state.get("trackId"),
                    "position": state.get("position"),
                    "isPlaying": state.get("isPlaying"),
                    "timestamp": time.time(),
                    "client_id": client_id,
                    # Ajouter des informations sur qui contrôle actuellement la lecture
                    "last_controller_id": state.get("last_controller_id"),
                    "last_client_id": state.get("last_client_id")
                })
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'état actuel: {str(e)}")
        
        # Si nous avons la file d'attente, l'envoyer aussi
        if room_code in self.room_queues:
            try:
                # Générer un ID client côté serveur pour ce message
                client_id = f"server_queue_{int(time.time())}"
                
                await websocket.send_json({
                    "type": "queue_sync",
                    "queue": self.room_queues[room_code],
                    "timestamp": time.time(),
                    "client_id": client_id
                })
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de la file d'attente: {str(e)}")
                
        # Informer le nouvel utilisateur qu'il peut contrôler la lecture
        try:
            await websocket.send_json({
                "type": "control_permission",
                "can_control": True,
                "timestamp": time.time(),
                "client_id": f"server_permission_{int(time.time())}"
            })
            logger.info(f"Permission de contrôle envoyée à l'utilisateur {user_id}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des permissions de contrôle: {str(e)}")
    
    def disconnect(self, room_code: str, user_id: int):
        if room_code in self.active_connections and user_id in self.active_connections[room_code]:
            del self.active_connections[room_code][user_id]
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]
                # Effacer l'état de la salle si elle est vide
                if room_code in self.room_states:
                    del self.room_states[room_code]
                # Effacer la file d'attente si la salle est vide
                if room_code in self.room_queues:
                    del self.room_queues[room_code]
            logger.info(f"Utilisateur {user_id} déconnecté de la salle {room_code}. Total restant: {self.get_users_count(room_code)}")
    
    async def broadcast(self, room_code: str, message: dict):
        if room_code in self.active_connections:
            # Ajouter un timestamp au message
            if "timestamp" not in message:
                message["timestamp"] = time.time()
            
            # Mettre à jour l'état de la salle si c'est un message de contrôle de lecture
            self._update_room_state(room_code, message)
            
            # Mettre à jour la file d'attente si nécessaire
            if message.get("type") == "queue_change":
                self._update_room_queue(room_code, message)
            
            disconnected_users = []
            for user_id, connection in list(self.active_connections[room_code].items()):
                try:
                    # Envoyer le message à tous les utilisateurs
                    # Les filtres seront gérés côté client
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
        if msg_type in ["play", "pause", "sync", "track_change", "seek"]:
            # Enregistrer l'ID de l'utilisateur qui a effectué l'action
            source_user_id = message.get("source_user_id")
            if source_user_id:
                self.room_states[room_code]["last_controller_id"] = source_user_id
                
            # Enregistrer l'ID client qui a effectué l'action
            client_id = message.get("client_id")
            if client_id:
                self.room_states[room_code]["last_client_id"] = client_id
            
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
            
            # Log détaillé
            log_details = f"État de la salle {room_code} mis à jour: " + \
                         f"type={msg_type}, " + \
                         f"trackId={self.room_states[room_code].get('trackId')}, " + \
                         f"position={self.room_states[room_code].get('position')}, " + \
                         f"isPlaying={self.room_states[room_code].get('isPlaying')}"
            
            if source_user_id:
                log_details += f", par user_id={source_user_id}"
            if client_id:
                log_details += f", client_id={client_id}"
                
            logger.info(log_details)
    
    def _update_room_queue(self, room_code: str, message: dict):
        """Met à jour la file d'attente de la salle."""
        if "queue" in message:
            self.room_queues[room_code] = message["queue"]
            logger.info(f"File d'attente de la salle {room_code} mise à jour, taille: {len(message['queue'])}")
    
    def _load_room_state(self, room_code: str, db: Session):
        """Charge l'état initial de la salle depuis la base de données."""
        try:
            # Récupérer la salle
            room = db.query(RoomModel).filter(RoomModel.room_code == room_code).first()
            if not room:
                return
            
            # Récupérer la file d'attente
            queue_items = (db.query(QueueItemModel, MusicModel)
                          .join(MusicModel, QueueItemModel.music_id == MusicModel.id)
                          .filter(QueueItemModel.room_id == room.id)
                          .order_by(QueueItemModel.position)
                          .all())
            
            # Initialiser la file d'attente
            self.room_queues[room_code] = []
            
            # Récupérer le premier élément de la file d'attente comme piste actuelle
            current_track_id = None
            if queue_items:
                queue_item, music = queue_items[0]
                current_track_id = music.id
                
                # Convertir les éléments de la file d'attente en format JSON
                self.room_queues[room_code] = [
                    {
                        "id": qi.id,
                        "room_id": qi.room_id,
                        "music_id": qi.music_id,
                        "position": qi.position,
                        "user_id": qi.user_id,
                        "music": {
                            "id": m.id,
                            "title": m.title,
                            "artist": m.artist,
                            "duration": m.duration,
                            "cover_path": m.cover_path
                        }
                    } for qi, m in queue_items
                ]
            
            # Initialiser l'état de lecture
            self.room_states[room_code] = {
                "trackId": current_track_id,
                "position": 0,
                "isPlaying": False,
                "timestamp": time.time()
            }
            
            logger.info(f"État initial de la salle {room_code} chargé, piste: {current_track_id}, file: {len(self.room_queues.get(room_code, []))}")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'état de la salle {room_code}: {str(e)}")
    
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
        await manager.connect(websocket, room_code, user_id, db)
        
        # Récupérer l'utilisateur s'il est connecté
        username = "Utilisateur"
        if user_id > 0:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user:
                username = user.username
        
        # Notifier les autres utilisateurs de la connexion
        await manager.broadcast(room_code, {
            "type": "user_joined",
            "user_id": user_id,
            "username": username,
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
                
                elif msg_type == "queue_change":
                    # Diffuser les changements de file d'attente
                    logger.info(f"Diffusion changement de file d'attente: {data}")
                    await manager.broadcast(room_code, data)
                    
                    # Si une mise à jour complète de la file d'attente est fournie
                    if "queue" in data:
                        manager.room_queues[room_code] = data["queue"]
                
                elif msg_type == "ping":
                    # Répondre au ping pour maintenir la connexion active
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                
                elif msg_type == "request_playback_state":
                    # Rediffuser la demande à tous les clients (un client répondra)
                    logger.info(f"Diffusion demande d'état de lecture pour {data.get('for_user_id')}")
                    await manager.broadcast(room_code, data)
                
                elif msg_type == "request_queue":
                    # Envoyer la file d'attente actuelle
                    if room_code in manager.room_queues:
                        await websocket.send_json({
                            "type": "queue_sync",
                            "queue": manager.room_queues[room_code],
                            "timestamp": time.time()
                        })
            
            except WebSocketDisconnect:
                manager.disconnect(room_code, user_id)
                await manager.broadcast(room_code, {
                    "type": "user_left",
                    "user_id": user_id,
                    "username": username,
                    "users_count": manager.get_users_count(room_code)
                })
                break
            
            except Exception as e:
                logger.error(f"Erreur WebSocket: {str(e)}")
                # Ne pas interrompre la boucle, tenter de continuer
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket déconnecté pour l'utilisateur {user_id}")
        manager.disconnect(room_code, user_id)
        
        # Notifier les autres utilisateurs de la déconnexion
        await manager.broadcast(room_code, {
            "type": "user_left",
            "user_id": user_id,
            "username": username if 'username' in locals() else "Utilisateur",
            "users_count": manager.get_users_count(room_code)
        })
    
    except Exception as e:
        logger.error(f"Erreur non gérée dans la connexion WebSocket: {str(e)}")
        # Tenter de déconnecter proprement en cas d'erreur
        manager.disconnect(room_code, user_id) 