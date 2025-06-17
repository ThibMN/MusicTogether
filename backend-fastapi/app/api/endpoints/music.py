from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import asyncio
import subprocess
import json
from pathlib import Path
from sqlalchemy import or_
import yt_dlp

from app.db.database import get_db
from app.schemas import Music, MusicCreate, MusicUpdate, MusicUpload
from app.models import Music as MusicModel, User as UserModel

router = APIRouter()

# Chemin de stockage des fichiers audio
AUDIO_STORAGE_PATH = Path("/app/storage/audio")
TEMP_STORAGE_PATH = Path("/app/storage/temp")

# Assurez-vous que les dossiers existent
AUDIO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
TEMP_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Fonction pour rechercher des musiques sur YouTube
async def search_youtube(query: str, max_results: int = 5):
    """
    Recherche des vidéos sur YouTube en utilisant yt-dlp.
    Retourne une liste de résultats avec titre, id, durée, etc.
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': False,
        'max_downloads': max_results
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Recherche sur YouTube avec le format de recherche ytsearch
            search_results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            
            if not search_results or 'entries' not in search_results:
                return []
            
            # Formater les résultats pour l'API
            formatted_results = []
            for entry in search_results['entries']:
                if entry:
                    formatted_results.append({
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Unknown Title'),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        'duration': entry.get('duration', 0),
                        'thumbnail': entry.get('thumbnail', ''),
                        'channel': entry.get('channel', 'Unknown Channel'),
                        'view_count': entry.get('view_count', 0)
                    })
            
            return formatted_results
    except Exception as e:
        print(f"Erreur lors de la recherche YouTube: {str(e)}")
        return []

# Fonction pour télécharger une musique depuis une URL
async def download_music_from_url(source_url: str, user_id: int, db: Session):
    """
    Télécharge une musique depuis une URL (YouTube, etc.) en utilisant yt-dlp.
    Cette fonction est exécutée en arrière-plan.
    """
    # Vérifier que l'utilisateur existe
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        print(f"Erreur: L'utilisateur avec l'ID {user_id} n'existe pas")
        # Utiliser un ID par défaut pour l'administrateur (à créer si nécessaire)
        admin_user = db.query(UserModel).filter(UserModel.username == "admin").first()
        if admin_user:
            user_id = admin_user.id
        else:
            # Créer un utilisateur admin par défaut
            admin_user = UserModel(
                username="admin",
                email="admin@musictogether.com",
                password="hashed_password_here"  # Dans un cas réel, utilisez un hash sécurisé
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            user_id = admin_user.id
    
    # Créer un nom de fichier temporaire unique
    temp_dir = TEMP_STORAGE_PATH
    output_template = str(temp_dir / '%(title)s.%(ext)s')
    
    # Options pour yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False
    }
    
    try:
        # Télécharger la vidéo et l'extraire en audio MP3
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_url, download=True)
            
            if not info:
                raise Exception("Échec de l'extraction des informations de la vidéo")
            
            # Récupérer les métadonnées
            title = info.get('title', 'Unknown Title')
            artist = info.get('artist', info.get('uploader', 'Unknown Artist'))
            album = info.get('album', 'YouTube')
            duration = info.get('duration', 0)
            
            # Déterminer le chemin du fichier téléchargé
            file_name = f"{title}.mp3"
            temp_file_path = temp_dir / file_name
            final_file_path = AUDIO_STORAGE_PATH / file_name
            
            # Déplacer le fichier vers le répertoire de stockage final
            if temp_file_path.exists():
                import shutil
                shutil.move(str(temp_file_path), str(final_file_path))
            else:
                # Chercher le fichier avec un nom similaire (yt-dlp peut modifier légèrement le nom)
                for file in temp_dir.glob("*.mp3"):
                    if title.lower() in file.name.lower():
                        shutil.move(str(file), str(final_file_path))
                        break
            
            # Extraire la miniature comme couverture si disponible
            cover_path = None
            if info.get('thumbnail'):
                try:
                    from PIL import Image
                    import requests
                    from io import BytesIO
                    
                    cover_file = AUDIO_STORAGE_PATH / f"{title}.jpg"
                    response = requests.get(info['thumbnail'])
                    img = Image.open(BytesIO(response.content))
                    img.save(str(cover_file))
                    cover_path = str(cover_file.relative_to(Path("/app")))
                except Exception as e:
                    print(f"Erreur lors de l'extraction de la couverture: {str(e)}")
            
            # Créer l'entrée dans la base de données
            db_music = MusicModel(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                file_path=str(final_file_path.relative_to(Path("/app"))),
                cover_path=cover_path,
                source_url=source_url,
                added_by=user_id
            )
            
            db.add(db_music)
            db.commit()
            db.refresh(db_music)
            
            return db_music
    except Exception as e:
        print(f"Erreur lors du téléchargement: {str(e)}")
        raise

@router.post("/search", response_model=List[dict])
async def search_music(query: str = Query(..., description="Terme de recherche pour trouver des musiques sur YouTube")):
    """
    Recherche des musiques sur YouTube en fonction du terme de recherche.
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Le terme de recherche doit contenir au moins 2 caractères")
    
    results = await search_youtube(query)
    return results

@router.post("/upload", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def upload_music(
    music_upload: MusicUpload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Télécharge une musique depuis une URL (YouTube, etc.).
    Le téléchargement est effectué en arrière-plan.
    """
    # Vérifier si l'URL est valide
    if not music_upload.source_url or not (
        music_upload.source_url.startswith("http://") or 
        music_upload.source_url.startswith("https://")
    ):
        raise HTTPException(status_code=400, detail="URL invalide")
    
    # Vérifier si la musique existe déjà
    existing_music = db.query(MusicModel).filter(MusicModel.source_url == music_upload.source_url).first()
    if existing_music:
        return {"message": "Cette musique existe déjà", "music_id": existing_music.id}
    
    # Simuler un ID utilisateur (à remplacer par l'authentification réelle)
    user_id = 1
    
    try:
        # Ajouter la tâche de téléchargement en arrière-plan
        background_tasks.add_task(download_music_from_url, music_upload.source_url, user_id, db)
        return {"message": "Téléchargement en cours"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du téléchargement: {str(e)}")

@router.get("/", response_model=List[Music])
def read_music(
    search: str = Query(None, description="Rechercher par titre, artiste ou album"),
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste des musiques avec possibilité de recherche.
    """
    query = db.query(MusicModel)
    
    # Appliquer le filtre de recherche si fourni
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                MusicModel.title.ilike(search_term),
                MusicModel.artist.ilike(search_term),
                MusicModel.album.ilike(search_term)
            )
        )
    
    # Appliquer pagination
    music = query.offset(skip).limit(limit).all()
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
    
    file_path = Path("/app") / db_music.file_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier audio non trouvé")
    
    def file_iterator():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk
    
    return StreamingResponse(
        file_iterator(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'}
    ) 