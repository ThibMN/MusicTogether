from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import os
import asyncio
from pathlib import Path

from app.db.database import get_db
from app.schemas import Music, MusicCreate, MusicUpdate, MusicUpload
from app.models import Music as MusicModel

router = APIRouter()

# Chemin de stockage des fichiers audio
AUDIO_STORAGE_PATH = Path("/app/storage/audio")
TEMP_STORAGE_PATH = Path("/app/storage/temp")

# Assurez-vous que les dossiers existent
AUDIO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
TEMP_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Fonction pour télécharger une musique depuis une URL (simulée)
async def download_music_from_url(source_url: str, user_id: int, db: Session):
    """
    Télécharge une musique depuis une URL (YouTube, etc.) en utilisant yt-dlp.
    Cette fonction est exécutée en arrière-plan.
    """
    # Simuler un téléchargement
    await asyncio.sleep(2)
    
    # Dans un cas réel, on utiliserait yt-dlp ici
    # Exemple (pseudo-code) :
    # result = subprocess.run(['yt-dlp', '-x', '--audio-format', 'mp3', source_url, '-o', temp_file])
    
    # Simuler les métadonnées extraites
    title = "Titre de la musique"
    artist = "Artiste"
    album = "Album"
    duration = 180.5  # en secondes
    
    # Simuler le chemin du fichier
    file_path = str(AUDIO_STORAGE_PATH / f"{hash(source_url)}.mp3")
    cover_path = str(AUDIO_STORAGE_PATH / f"{hash(source_url)}.jpg")
    
    # Créer l'entrée dans la base de données
    db_music = MusicModel(
        title=title,
        artist=artist,
        album=album,
        duration=duration,
        file_path=file_path,
        cover_path=cover_path,
        source_url=source_url,
        added_by=user_id
    )
    
    db.add(db_music)
    db.commit()

@router.post("/upload", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def upload_music(
    music_upload: MusicUpload,
    background_tasks: BackgroundTasks,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Télécharge une musique depuis une URL (YouTube, etc.).
    Le téléchargement est effectué en arrière-plan.
    """
    # Vérifier si la musique existe déjà
    existing_music = db.query(MusicModel).filter(MusicModel.source_url == music_upload.source_url).first()
    if existing_music:
        return {"message": "Cette musique existe déjà", "music_id": existing_music.id}
    
    # Ajouter la tâche de téléchargement en arrière-plan
    background_tasks.add_task(download_music_from_url, music_upload.source_url, user_id, db)
    
    return {"message": "Téléchargement en cours"}

@router.get("/", response_model=List[Music])
def read_music(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupérer la liste des musiques.
    """
    music = db.query(MusicModel).offset(skip).limit(limit).all()
    return music

@router.get("/{music_id}", response_model=Music)
def read_music_item(music_id: int, db: Session = Depends(get_db)):
    """
    Récupérer une musique spécifique par son ID.
    """
    db_music = db.query(MusicModel).filter(MusicModel.id == music_id).first()
    if db_music is None:
        raise HTTPException(status_code=404, detail="Musique non trouvée")
    return db_music

@router.put("/{music_id}", response_model=Music)
def update_music(music_id: int, music: MusicUpdate, db: Session = Depends(get_db)):
    """
    Mettre à jour une musique.
    """
    db_music = db.query(MusicModel).filter(MusicModel.id == music_id).first()
    if db_music is None:
        raise HTTPException(status_code=404, detail="Musique non trouvée")
    
    for key, value in music.dict(exclude_unset=True).items():
        setattr(db_music, key, value)
    
    db.commit()
    db.refresh(db_music)
    return db_music

@router.get("/{music_id}/stream")
def stream_music(music_id: int, db: Session = Depends(get_db)):
    """
    Streamer une musique.
    """
    db_music = db.query(MusicModel).filter(MusicModel.id == music_id).first()
    if db_music is None:
        raise HTTPException(status_code=404, detail="Musique non trouvée")
    
    # Dans un cas réel, on vérifierait que le fichier existe
    # et on utiliserait StreamingResponse pour le streamer
    
    # Simuler un streaming de fichier
    def fake_file_sender():
        yield b"Audio content simulation"
    
    return StreamingResponse(
        fake_file_sender(),
        media_type="audio/mpeg"
    ) 