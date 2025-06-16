from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func

from app.db.database import get_db
from app.schemas import (
    Playlist, PlaylistCreate, PlaylistUpdate, PlaylistDetail,
    PlaylistItem, PlaylistItemCreate, PlaylistItemUpdate,
    Favorite, FavoriteCreate, Music
)
from app.models import (
    Playlist as PlaylistModel,
    PlaylistItem as PlaylistItemModel,
    Favorite as FavoriteModel,
    Music as MusicModel
)

router = APIRouter()

# --- Playlists ---

@router.post("/", response_model=Playlist, status_code=status.HTTP_201_CREATED)
def create_playlist(playlist: PlaylistCreate, user_id: int, db: Session = Depends(get_db)):
    """
    Créer une nouvelle playlist.
    """
    db_playlist = PlaylistModel(
        name=playlist.name,
        user_id=user_id
    )
    db.add(db_playlist)
    db.commit()
    db.refresh(db_playlist)
    return db_playlist

@router.get("/user/{user_id}", response_model=List[Playlist])
def get_user_playlists(user_id: int, db: Session = Depends(get_db)):
    """
    Récupérer les playlists d'un utilisateur.
    """
    playlists = db.query(PlaylistModel).filter(PlaylistModel.user_id == user_id).all()
    return playlists

@router.get("/{playlist_id}", response_model=PlaylistDetail)
def get_playlist(playlist_id: int, db: Session = Depends(get_db)):
    """
    Récupérer une playlist avec ses morceaux.
    """
    playlist = db.query(PlaylistModel).filter(PlaylistModel.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist non trouvée")
    
    # Récupérer les morceaux de la playlist
    items = db.query(
        PlaylistItemModel, MusicModel
    ).join(
        MusicModel, PlaylistItemModel.music_id == MusicModel.id
    ).filter(
        PlaylistItemModel.playlist_id == playlist_id
    ).order_by(
        PlaylistItemModel.position
    ).all()
    
    # Créer l'objet de réponse
    result = playlist.__dict__.copy()
    result["items"] = [music for _, music in items]
    
    return result

@router.put("/{playlist_id}", response_model=Playlist)
def update_playlist(playlist_id: int, playlist: PlaylistUpdate, user_id: int, db: Session = Depends(get_db)):
    """
    Mettre à jour une playlist.
    """
    db_playlist = db.query(PlaylistModel).filter(
        PlaylistModel.id == playlist_id,
        PlaylistModel.user_id == user_id  # Vérifier que l'utilisateur est bien le propriétaire
    ).first()
    
    if not db_playlist:
        raise HTTPException(status_code=404, detail="Playlist non trouvée ou vous n'êtes pas autorisé à la modifier")
    
    for key, value in playlist.dict(exclude_unset=True).items():
        setattr(db_playlist, key, value)
    
    db.commit()
    db.refresh(db_playlist)
    return db_playlist

@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(playlist_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Supprimer une playlist.
    """
    db_playlist = db.query(PlaylistModel).filter(
        PlaylistModel.id == playlist_id,
        PlaylistModel.user_id == user_id  # Vérifier que l'utilisateur est bien le propriétaire
    ).first()
    
    if not db_playlist:
        raise HTTPException(status_code=404, detail="Playlist non trouvée ou vous n'êtes pas autorisé à la supprimer")
    
    db.delete(db_playlist)
    db.commit()
    return None

# --- Playlist Items ---

@router.post("/items", response_model=PlaylistItem, status_code=status.HTTP_201_CREATED)
def add_to_playlist(item: PlaylistItemCreate, user_id: int, db: Session = Depends(get_db)):
    """
    Ajouter un morceau à une playlist.
    """
    # Vérifier que la playlist existe et appartient à l'utilisateur
    playlist = db.query(PlaylistModel).filter(
        PlaylistModel.id == item.playlist_id,
        PlaylistModel.user_id == user_id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist non trouvée ou vous n'êtes pas autorisé à la modifier")
    
    # Vérifier que la musique existe
    music = db.query(MusicModel).filter(MusicModel.id == item.music_id).first()
    if not music:
        raise HTTPException(status_code=404, detail="Musique non trouvée")
    
    # Vérifier si le morceau est déjà dans la playlist
    existing_item = db.query(PlaylistItemModel).filter(
        PlaylistItemModel.playlist_id == item.playlist_id,
        PlaylistItemModel.music_id == item.music_id
    ).first()
    
    if existing_item:
        raise HTTPException(status_code=400, detail="Ce morceau est déjà dans la playlist")
    
    # Déterminer la position dans la playlist
    max_position = db.query(func.max(PlaylistItemModel.position)).filter(
        PlaylistItemModel.playlist_id == item.playlist_id
    ).scalar() or 0
    
    # Créer l'élément de playlist
    db_item = PlaylistItemModel(
        playlist_id=item.playlist_id,
        music_id=item.music_id,
        position=max_position + 1  # Ajouter à la fin de la playlist
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/items/{item_id}", response_model=PlaylistItem)
def update_playlist_item(item_id: int, item_update: PlaylistItemUpdate, user_id: int, db: Session = Depends(get_db)):
    """
    Mettre à jour la position d'un morceau dans une playlist.
    """
    # Récupérer l'élément de playlist
    db_item = db.query(PlaylistItemModel).filter(PlaylistItemModel.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Élément de playlist non trouvé")
    
    # Vérifier que l'utilisateur est propriétaire de la playlist
    playlist = db.query(PlaylistModel).filter(
        PlaylistModel.id == db_item.playlist_id,
        PlaylistModel.user_id == user_id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à modifier cette playlist")
    
    # Mettre à jour la position
    if "position" in item_update.dict(exclude_unset=True):
        current_position = db_item.position
        new_position = item_update.position
        
        # Récupérer tous les éléments de la playlist
        playlist_items = db.query(PlaylistItemModel).filter(
            PlaylistItemModel.playlist_id == db_item.playlist_id
        ).order_by(PlaylistItemModel.position).all()
        
        # Réorganiser les positions
        if new_position < current_position:
            # Déplacer vers le haut
            for item in playlist_items:
                if new_position <= item.position < current_position:
                    item.position += 1
        elif new_position > current_position:
            # Déplacer vers le bas
            for item in playlist_items:
                if current_position < item.position <= new_position:
                    item.position -= 1
        
        # Mettre à jour la position de l'élément
        db_item.position = new_position
    
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist_item(item_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Supprimer un morceau d'une playlist.
    """
    # Récupérer l'élément de playlist
    db_item = db.query(PlaylistItemModel).filter(PlaylistItemModel.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Élément de playlist non trouvé")
    
    # Vérifier que l'utilisateur est propriétaire de la playlist
    playlist = db.query(PlaylistModel).filter(
        PlaylistModel.id == db_item.playlist_id,
        PlaylistModel.user_id == user_id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à modifier cette playlist")
    
    # Récupérer la position de l'élément à supprimer
    position_to_remove = db_item.position
    playlist_id = db_item.playlist_id
    
    # Supprimer l'élément
    db.delete(db_item)
    
    # Mettre à jour les positions des éléments suivants
    db.query(PlaylistItemModel).filter(
        PlaylistItemModel.playlist_id == playlist_id,
        PlaylistItemModel.position > position_to_remove
    ).update({"position": PlaylistItemModel.position - 1})
    
    db.commit()
    return None

# --- Favorites ---

@router.post("/favorites", response_model=Favorite, status_code=status.HTTP_201_CREATED)
def add_favorite(favorite: FavoriteCreate, user_id: int, db: Session = Depends(get_db)):
    """
    Ajouter un morceau aux favoris.
    """
    # Vérifier que la musique existe
    music = db.query(MusicModel).filter(MusicModel.id == favorite.music_id).first()
    if not music:
        raise HTTPException(status_code=404, detail="Musique non trouvée")
    
    # Vérifier si le morceau est déjà dans les favoris
    existing_favorite = db.query(FavoriteModel).filter(
        FavoriteModel.user_id == user_id,
        FavoriteModel.music_id == favorite.music_id
    ).first()
    
    if existing_favorite:
        raise HTTPException(status_code=400, detail="Ce morceau est déjà dans vos favoris")
    
    # Créer le favori
    db_favorite = FavoriteModel(
        user_id=user_id,
        music_id=favorite.music_id
    )
    
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite

@router.get("/favorites/user/{user_id}", response_model=List[Music])
def get_user_favorites(user_id: int, db: Session = Depends(get_db)):
    """
    Récupérer les favoris d'un utilisateur.
    """
    favorites = db.query(MusicModel).join(
        FavoriteModel, FavoriteModel.music_id == MusicModel.id
    ).filter(
        FavoriteModel.user_id == user_id
    ).all()
    
    return favorites

@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(favorite_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Supprimer un favori.
    """
    db_favorite = db.query(FavoriteModel).filter(
        FavoriteModel.id == favorite_id,
        FavoriteModel.user_id == user_id  # Vérifier que l'utilisateur est bien le propriétaire
    ).first()
    
    if not db_favorite:
        raise HTTPException(status_code=404, detail="Favori non trouvé ou vous n'êtes pas autorisé à le supprimer")
    
    db.delete(db_favorite)
    db.commit()
    return None 