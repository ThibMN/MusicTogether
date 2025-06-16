from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.db.database import engine, Base
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Créer les tables dans la base de données
Base.metadata.create_all(bind=engine)

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

# Inclure les routes
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API MusicTogether"}