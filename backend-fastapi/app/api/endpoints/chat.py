from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from app.db.database import get_db
from app.schemas import ChatMessage, ChatMessageCreate, ChatMessageResponse
from app.models import ChatMessage as ChatMessageModel, Room as RoomModel, User as UserModel
from app.api.endpoints.rooms import manager as room_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ChatMessage, status_code=status.HTTP_201_CREATED)
def create_message(message: ChatMessageCreate, db: Session = Depends(get_db)):
    """
    Créer un nouveau message dans le chat d'une salle.
    """
    logger.info(f"Tentative de création de message: {message.dict()}")
    
    try:
        # Vérifier que la salle existe
        room = db.query(RoomModel).filter(RoomModel.id == message.room_id).first()
        if not room:
            logger.error(f"Salle non trouvée: {message.room_id}")
            raise HTTPException(status_code=404, detail="Salle non trouvée")
        
        # Vérifier que le message n'est pas trop long
        if len(message.message) > 200:
            logger.error(f"Message trop long: {len(message.message)} caractères")
            raise HTTPException(status_code=400, detail="Le message ne peut pas dépasser 200 caractères")
        
        # Vérifier que l'utilisateur existe
        user_id = message.user_id
        logger.info(f"Recherche de l'utilisateur avec ID: {user_id}")
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            logger.error(f"Utilisateur non trouvé: {user_id}")
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        logger.info(f"Création du message pour l'utilisateur: {user.username} dans la salle: {room.room_code}")
        
        # Créer le message
        db_message = ChatMessageModel(
            room_id=message.room_id,
            user_id=user_id,
            message=message.message
        )
        
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        
        logger.info(f"Message créé avec succès, ID: {db_message.id}")
        
        # Notifier les clients via WebSocket
        room_code = room.room_code
        websocket_payload = {
            "type": "chat_message",
            "message": {
                "id": db_message.id,
                "user_id": user_id,
                "username": user.username,
                "message": db_message.message,
                "sent_at": db_message.sent_at.isoformat()
            }
        }
        logger.info(f"Diffusion du message via WebSocket: {websocket_payload}")
        room_manager.broadcast(room_code, websocket_payload)
        
        return db_message
    except Exception as e:
        logger.exception(f"Erreur lors de la création du message: {str(e)}")
        raise

@router.get("/room/{room_id}", response_model=List[ChatMessageResponse])
def get_room_messages(room_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """
    Récupérer les messages d'une salle.
    """
    # Vérifier que la salle existe
    room = db.query(RoomModel).filter(RoomModel.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Salle non trouvée")
    
    # Récupérer les messages triés par date d'envoi (les plus récents en premier)
    messages = db.query(
        ChatMessageModel, UserModel.username
    ).join(
        UserModel, ChatMessageModel.user_id == UserModel.id
    ).filter(
        ChatMessageModel.room_id == room_id
    ).order_by(
        ChatMessageModel.sent_at.desc()
    ).limit(limit).all()
    
    # Convertir en format de réponse
    result = []
    for message, username in messages:
        result.append({
            "id": message.id,
            "room_id": message.room_id,
            "user_id": message.user_id,
            "username": username,
            "message": message.message,
            "sent_at": message.sent_at
        })
    
    # Inverser pour avoir les messages dans l'ordre chronologique
    result.reverse()
    
    return result 