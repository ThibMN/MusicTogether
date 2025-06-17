from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import base64
import json
import hmac
import hashlib
import os
from datetime import datetime

from app.db.database import get_db
from app.schemas import User, UserCreate, UserUpdate, UserLogin, TokenResponse
from app.models import User as UserModel

router = APIRouter()

# Clé secrète pour les JWT (à synchroniser avec le service PHP)
JWT_SECRET = os.environ.get("JWT_SECRET", "musictogether_secret_key_change_in_prod")

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Créer un nouvel utilisateur. Cette route est principalement utilisée par le service PHP.
    """
    db_user = UserModel(
        username=user.username,
        email=user.email,
        password=user.password  # Dans un cas réel, il faudrait hasher le mot de passe
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupérer la liste des utilisateurs.
    """
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Récupérer un utilisateur spécifique par son ID.
    """
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return db_user

@router.put("/{user_id}", response_model=User)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    """
    Mettre à jour un utilisateur.
    """
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/validate-token", response_model=TokenResponse)
def validate_token(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    Valide un token JWT fourni par le service PHP d'authentification.
    Retourne les informations de l'utilisateur si le token est valide.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification manquant ou invalide"
        )
    
    token = authorization.split(" ")[1]
    
    try:
        # Dans un cas réel, utiliser une bibliothèque JWT appropriée
        # Ici on simule juste un token simple
        token_parts = token.split('.')
        if len(token_parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Format de token invalide"
            )
        
        payload_b64 = token_parts[0]
        signature = token_parts[1]
        
        # Vérifier la signature
        expected_signature = hmac.new(
            JWT_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature du token invalide"
            )
        
        # Décoder le payload
        payload = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
        
        # Vérifier si le token est expiré
        if payload.get('exp', 0) < datetime.now().timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expiré"
            )
        
        # Vérifier que l'utilisateur existe toujours
        user_id = payload.get('user_id')
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur introuvable"
            )
        
        # Retourner les informations de l'utilisateur
        return {
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        }
        
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalide: {str(e)}"
        ) 