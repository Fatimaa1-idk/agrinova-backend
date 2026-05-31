from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Utilisateur
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "agrinova-secret-2024")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/connexion")


def hasher_mdp(mdp: str) -> str:
    return pwd_context.hash(mdp)


def verifier_mdp(mdp: str, hash_stocke: str) -> bool:
    # Support legacy SHA256 hashes during migration
    import hashlib
    sha_hash = hashlib.sha256(mdp.encode()).hexdigest()
    if sha_hash == hash_stocke:
        return True
    try:
        return pwd_context.verify(mdp, hash_stocke)
    except Exception:
        return False


def creer_token(email: str, role: str, user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    data = {"sub": email, "role": role, "id": user_id, "exp": expire}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def get_utilisateur_actuel(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    erreur = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise erreur
    except JWTError:
        raise erreur

    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if not user:
        raise erreur
    return user


def exiger_producteur(user: Utilisateur = Depends(get_utilisateur_actuel)):
    if user.role != "producteur":
        raise HTTPException(status_code=403, detail="Réservé aux producteurs")
    return user


def exiger_acheteur(user: Utilisateur = Depends(get_utilisateur_actuel)):
    if user.role != "acheteur":
        raise HTTPException(status_code=403, detail="Réservé aux acheteurs")
    return user
