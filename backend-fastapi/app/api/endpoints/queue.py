from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func

from app.db.database import get_db
from app.schemas import QueueItem, QueueItemCreate, QueueItemUpdate, QueueItemDetail
from app.models import QueueItem as QueueItemModel, Room as RoomModel, Music as MusicModel

router = APIRouter()

@router.post("/", response_model=QueueItem, status_code=status.HTTP_201_CREATED)
def add_to_queue(queue_item: QueueItemCreate, db: Session = Depends(get_db)):
    """
    Ajouter une musique à la file d'attente d'une salle.
    """
    # Vérifier que la salle existe
    room = db.query(RoomModel).filter(RoomModel.id == queue_item.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Salle non trouvée")
    
    # Vérifier que la musique existe
    music = db.query(MusicModel).filter(MusicModel.id == queue_item.music_id).first()
    if not music:
        raise HTTPException(status_code=404, detail="Musique non trouvée")
    
    # Déterminer la position dans la file d'attente si non fournie
    position = queue_item.position
    if position is None:
        max_position = db.query(func.max(QueueItemModel.position)).filter(
            QueueItemModel.room_id == queue_item.room_id
        ).scalar() or 0
        position = max_position + 1
    
    # Simuler un ID utilisateur (à remplacer par l'authentification réelle)
    user_id = 1
    
    # Créer l'élément de file d'attente
    db_queue_item = QueueItemModel(
        room_id=queue_item.room_id,
        music_id=queue_item.music_id,
        position=position,
        added_by=user_id
    )
    
    db.add(db_queue_item)
    db.commit()
    db.refresh(db_queue_item)
    
    # Notifier les clients via WebSocket (si implémenté)
    # TODO: Utiliser le ConnectionManager de rooms.py pour notifier les clients
    
    return db_queue_item

@router.post("/items", response_model=QueueItem, status_code=status.HTTP_201_CREATED)
def add_to_queue_items(queue_item: QueueItemCreate, db: Session = Depends(get_db)):
    """
    Endpoint alternatif pour ajouter une musique à la file d'attente d'une salle.
    """
    # Utiliser la même logique que l'endpoint principal
    return add_to_queue(queue_item, db)

@router.get("/room/{room_id}", response_model=List[QueueItemDetail])
def get_room_queue(room_id: int, db: Session = Depends(get_db)):
    """
    Récupérer la file d'attente d'une salle.
    """
    # Vérifier que la salle existe
    room = db.query(RoomModel).filter(RoomModel.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Salle non trouvée")
    
    # Récupérer la file d'attente triée par position
    queue_items = db.query(QueueItemModel).filter(
        QueueItemModel.room_id == room_id
    ).order_by(QueueItemModel.position).all()
    
    return queue_items

@router.get("/rooms/{room_id}", response_model=List[QueueItemDetail])
def get_room_queue_alt(room_id: int, db: Session = Depends(get_db)):
    """
    Endpoint alternatif pour récupérer la file d'attente d'une salle.
    """
    # Utiliser la même logique que l'endpoint principal
    return get_room_queue(room_id, db)

@router.put("/{queue_item_id}", response_model=QueueItem)
def update_queue_item(queue_item_id: int, item_update: QueueItemUpdate, db: Session = Depends(get_db)):
    """
    Mettre à jour un élément de la file d'attente (changer sa position).
    """
    db_queue_item = db.query(QueueItemModel).filter(QueueItemModel.id == queue_item_id).first()
    if not db_queue_item:
        raise HTTPException(status_code=404, detail="Élément de file d'attente non trouvé")
    
    # Récupérer tous les éléments de la file d'attente pour cette salle
    room_queue = db.query(QueueItemModel).filter(
        QueueItemModel.room_id == db_queue_item.room_id
    ).order_by(QueueItemModel.position).all()
    
    # Supprimer l'élément de sa position actuelle
    current_position = db_queue_item.position
    new_position = item_update.position
    
    # Réorganiser les positions des autres éléments
    if new_position < current_position:
        # Déplacer vers le haut: incrémenter les positions des éléments entre new et current
        for item in room_queue:
            if new_position <= item.position < current_position:
                item.position += 1
    elif new_position > current_position:
        # Déplacer vers le bas: décrémenter les positions des éléments entre current et new
        for item in room_queue:
            if current_position < item.position <= new_position:
                item.position -= 1
    
    # Mettre à jour la position de l'élément
    db_queue_item.position = new_position
    
    db.commit()
    db.refresh(db_queue_item)
    
    # Notifier les clients via WebSocket (si implémenté)
    # TODO: Utiliser le ConnectionManager de rooms.py pour notifier les clients
    
    return db_queue_item

@router.delete("/{queue_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_queue_item(queue_item_id: int, db: Session = Depends(get_db)):
    """
    Supprimer un élément de la file d'attente.
    """
    db_queue_item = db.query(QueueItemModel).filter(QueueItemModel.id == queue_item_id).first()
    if not db_queue_item:
        raise HTTPException(status_code=404, detail="Élément de file d'attente non trouvé")
    
    # Récupérer la position de l'élément à supprimer
    position_to_remove = db_queue_item.position
    room_id = db_queue_item.room_id
    
    # Supprimer l'élément
    db.delete(db_queue_item)
    
    # Mettre à jour les positions des éléments suivants
    db.query(QueueItemModel).filter(
        QueueItemModel.room_id == room_id,
        QueueItemModel.position > position_to_remove
    ).update({"position": QueueItemModel.position - 1})
    
    db.commit()
    
    # Notifier les clients via WebSocket (si implémenté)
    # TODO: Utiliser le ConnectionManager de rooms.py pour notifier les clients
    
    return None 