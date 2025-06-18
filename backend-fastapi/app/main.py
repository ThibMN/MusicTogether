from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.db.database import engine, Base
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Créer les tables dans la base de données
Base.metadata.create_all(bind=engine)

# Créer les dossiers de stockage s'ils n'existent pas
storage_path = Path("/app/storage")
storage_path.mkdir(parents=True, exist_ok=True)
(storage_path / "audio").mkdir(exist_ok=True)
(storage_path / "temp").mkdir(exist_ok=True)

app = FastAPI(
    title="MusicTogether API",
    description="API pour l'application MusicTogether",
    version="0.1.0"
)

# Configuration CORS
origins = [
    "http://localhost:3000",  # Frontend Vue.js
    "http://localhost:8080",  # PHP Auth
    "http://frontend:3000",   # Frontend dans Docker
    "http://php:8080",        # PHP Auth dans Docker
    "*",                      # Toutes les origines (temporairement pour le debug)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Accepter toutes les origines pour le debug
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monter le dossier de stockage pour servir les fichiers statiques
app.mount("/storage", StaticFiles(directory="/app/storage"), name="storage")

# Inclure les routes
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API MusicTogether"}