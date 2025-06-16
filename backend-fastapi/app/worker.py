from celery import Celery
import os
import subprocess
import logging
from pathlib import Path

# Configuration Celery
celery_app = Celery(
    "music_worker",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2"
)

# Configuration des tâches
celery_app.conf.task_routes = {
    "app.worker.download_music": "music-queue",
    "app.worker.process_audio": "audio-queue",
}

# Chemins de stockage
AUDIO_STORAGE_PATH = Path("/app/storage/audio")
TEMP_STORAGE_PATH = Path("/app/storage/temp")

# Assurez-vous que les dossiers existent
AUDIO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
TEMP_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

@celery_app.task(bind=True, name="app.worker.download_music")
def download_music(self, source_url, user_id):
    """
    Télécharge une musique depuis une URL (YouTube, etc.) en utilisant yt-dlp.
    """
    logging.info(f"Téléchargement de la musique depuis {source_url}")
    
    # Générer un nom de fichier unique basé sur l'URL
    file_hash = abs(hash(source_url))
    temp_file = str(TEMP_STORAGE_PATH / f"{file_hash}.%(ext)s")
    
    try:
        # Télécharger la vidéo et extraire l'audio avec yt-dlp
        result = subprocess.run([
            'yt-dlp',
            '-x',  # Extraire l'audio
            '--audio-format', 'mp3',  # Format audio
            '--audio-quality', '0',  # Meilleure qualité
            '--embed-thumbnail',  # Intégrer la miniature
            '--add-metadata',  # Ajouter les métadonnées
            source_url,
            '-o', temp_file
        ], check=True, capture_output=True, text=True)
        
        # Récupérer le chemin du fichier téléchargé
        output_file = temp_file.replace("%(ext)s", "mp3")
        
        # Déplacer le fichier vers le stockage permanent
        final_path = str(AUDIO_STORAGE_PATH / f"{file_hash}.mp3")
        os.rename(output_file, final_path)
        
        # Extraire la miniature pour la cover
        cover_path = str(AUDIO_STORAGE_PATH / f"{file_hash}.jpg")
        
        # TODO: Extraire les métadonnées et mettre à jour la base de données
        # Cette partie nécessiterait une interaction avec la base de données
        
        return {
            "status": "success",
            "file_path": final_path,
            "cover_path": cover_path,
            "source_url": source_url
        }
    
    except Exception as e:
        logging.error(f"Erreur lors du téléchargement: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "source_url": source_url
        }

@celery_app.task(bind=True, name="app.worker.process_audio")
def process_audio(self, file_path, options=None):
    """
    Traite un fichier audio (conversion, normalisation, etc.).
    """
    logging.info(f"Traitement du fichier audio {file_path}")
    
    if not options:
        options = {}
    
    try:
        # Exemple de traitement avec ffmpeg
        output_file = file_path.replace(".mp3", "_processed.mp3")
        
        # Construire la commande ffmpeg en fonction des options
        cmd = ['ffmpeg', '-i', file_path]
        
        # Ajouter des options de traitement
        if options.get('normalize', False):
            cmd.extend(['-filter:a', 'loudnorm'])
        
        if options.get('bitrate'):
            cmd.extend(['-b:a', options['bitrate']])
        
        cmd.append(output_file)
        
        # Exécuter la commande
        subprocess.run(cmd, check=True, capture_output=True)
        
        return {
            "status": "success",
            "input_file": file_path,
            "output_file": output_file
        }
    
    except Exception as e:
        logging.error(f"Erreur lors du traitement audio: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        } 