from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Récupérer l'URL de la base de données depuis les variables d'environnement
DATABASE_URL = os.getenv("DATABASE_URL", "mariadb://root:password@mariadb/musicdb")

# Créer le moteur SQLAlchemy
engine = create_engine(DATABASE_URL)

# Créer une classe de session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Créer une classe de base pour les modèles
Base = declarative_base()

def get_db():
    """
    Fonction pour obtenir une session de base de données.
    À utiliser comme dépendance dans les routes FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()