from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, File, UploadFile, Form
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
import mutagen

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
    print(f"Recherche YouTube pour la requête: '{query}', max_results: {max_results}")
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': False,
        'max_downloads': max_results
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Recherche sur YouTube avec le format de recherche ytsearch
            search_query = f"ytsearch{max_results}:{query}"
            print(f"Requête yt-dlp: {search_query}")
            
            search_results = ydl.extract_info(search_query, download=False)
            
            if not search_results:
                print("Aucun résultat retourné par yt-dlp")
                return []
                
            if 'entries' not in search_results:
                print("Pas d'entrées dans les résultats de recherche:", search_results.keys())
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
            
            print(f"Résultats trouvés: {len(formatted_results)}")
            return formatted_results
    except Exception as e:
        print(f"Erreur lors de la recherche YouTube: {str(e)}")
        import traceback
        traceback.print_exc()
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
                    import re
                    
                    # Créer l'entrée dans la base de données d'abord pour avoir l'ID
                    db_music = MusicModel(
                        title=title,
                        artist=artist,
                        album=album,
                        duration=duration,
                        file_path=str(final_file_path.relative_to(Path("/app"))),
                        cover_path=None,  # On le mettra à jour après
                        source_url=source_url,
                        added_by=user_id
                    )
                    
                    db.add(db_music)
                    db.commit()
                    db.refresh(db_music)
                    
                    # Utiliser l'ID comme nom de fichier pour éviter les problèmes de caractères spéciaux
                    cover_filename = f"cover_{db_music.id}.jpg"
                    cover_file = AUDIO_STORAGE_PATH / cover_filename
                    
                    response = requests.get(info['thumbnail'])
                    img = Image.open(BytesIO(response.content))
                    img.save(str(cover_file))
                    
                    # Mettre à jour le chemin de la cover dans la base de données
                    cover_path = f"/storage/audio/{cover_filename}"
                    db_music.cover_path = cover_path
                    db.commit()
                    db.refresh(db_music)
                    
                    return db_music
                    
                except Exception as e:
                    print(f"Erreur lors de l'extraction de la couverture: {str(e)}")
            
            # Si pas de miniature ou erreur, créer l'entrée sans cover
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
@router.get("/search", response_model=List[dict])
async def search_music(query: str = Query(..., description="Terme de recherche pour trouver des musiques sur YouTube")):
    """
    Recherche des musiques sur YouTube en fonction du terme de recherche.
    """
    print(f"Requête de recherche reçue pour: '{query}'")
    
    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Le terme de recherche doit contenir au moins 2 caractères")
    
    try:
        results = await search_youtube(query)
        print(f"Nombre de résultats trouvés: {len(results)}")
        return results
    except Exception as e:
        print(f"Erreur non gérée dans l'endpoint search: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(e)}")

@router.post("/upload", response_model=dict, status_code=status.HTTP_200_OK)
async def upload_music(
    music_upload: MusicUpload,
    db: Session = Depends(get_db)
):
    """
    Télécharge une musique depuis une URL (YouTube, etc.).
    """
    # Vérifier si l'URL est valide
    if not music_upload.source_url or not (
        music_upload.source_url.startswith("http://") or 
        music_upload.source_url.startswith("https://")
    ):
        raise HTTPException(status_code=400, detail="URL invalide")
    
    # Vérifier si la musique existe déjà avec cette URL source
    existing_music = db.query(MusicModel).filter(MusicModel.source_url == music_upload.source_url).first()
    if existing_music:
        print(f"Musique déjà existante avec l'ID {existing_music.id}")
        return {"message": "Cette musique existe déjà", "music_id": existing_music.id}
    
    # Simuler un ID utilisateur (à remplacer par l'authentification réelle)
    user_id = 1
    
    try:
        # Exécuter le téléchargement de manière synchrone
        db_music = await download_music_from_url(music_upload.source_url, user_id, db)
        return {"message": "Téléchargement réussi", "music_id": db_music.id}
    except Exception as e:
        print(f"Erreur lors du téléchargement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du téléchargement: {str(e)}")

@router.post("/upload-file", response_model=dict, status_code=status.HTTP_200_OK)
async def upload_music_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload d'un fichier audio local (mp3, wav, etc.).
    """
    # Vérifier l'extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"]:
        raise HTTPException(status_code=400, detail="Format de fichier non supporté")

    # Générer un nom de fichier unique
    import uuid
    unique_id = str(uuid.uuid4())
    new_filename = f"{unique_id}{ext}"
    dest_path = AUDIO_STORAGE_PATH / new_filename

    # Sauvegarder le fichier
    with open(dest_path, "wb") as buffer:
        buffer.write(await file.read())

    # Extraire les métadonnées
    title = os.path.splitext(filename)[0]
    artist = "Inconnu"
    album = None
    duration = 0.0
    try:
        audio = mutagen.File(dest_path)
        if audio:
            duration = float(audio.info.length) if hasattr(audio.info, 'length') else 0.0
            if audio.tags:
                title = audio.tags.get('TIT2', title)
                artist = audio.tags.get('TPE1', artist)
                album = audio.tags.get('TALB', album)
                # Certains formats utilisent d'autres clés
                if isinstance(title, list):
                    title = title[0]
                if isinstance(artist, list):
                    artist = artist[0]
                if isinstance(album, list):
                    album = album[0]
    except Exception as e:
        print(f"Erreur extraction métadonnées: {e}")

    # Créer l'entrée en base
    user_id = 1  # TODO: remplacer par l'utilisateur authentifié
    db_music = MusicModel(
        title=str(title),
        artist=str(artist),
        album=str(album) if album else None,
        duration=duration,
        file_path=str(dest_path.relative_to(Path("/app"))),
        cover_path=None,
        source_url=None,
        added_by=user_id
    )
    db.add(db_music)
    db.commit()
    db.refresh(db_music)

    return {"message": "Upload réussi", "music_id": db_music.id}

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