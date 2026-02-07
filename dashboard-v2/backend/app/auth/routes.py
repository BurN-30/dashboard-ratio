"""
Routes d'authentification.
"""
import hmac
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings
from app.auth.jwt import create_access_token, get_current_user, TokenResponse, TokenData
from fastapi import Depends

router = APIRouter()
settings = get_settings()


class LoginRequest(BaseModel):
    """Corps de la requete de login."""
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Reponse du login."""
    success: bool
    token: TokenResponse


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authentifie l'utilisateur et retourne un JWT.

    - Verifie le mot de passe contre ADMIN_PASSWORD
    - Retourne un token JWT signe
    """
    if not hmac.compare_digest(request.password, settings.admin_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe incorrect"
        )

    # Creer le token (duree etendue si "remember me")
    from datetime import timedelta
    expires = timedelta(days=30) if request.remember_me else None

    token = create_access_token(subject="admin", expires_delta=expires)

    return LoginResponse(success=True, token=token)


@router.post("/logout")
async def logout():
    """
    Deconnexion (cote client, invalider le token).

    Note: Les JWT sont stateless, donc le "logout" est gere cote client
    en supprimant le token. Pour un vrai logout server-side, il faudrait
    implementer une blacklist de tokens.
    """
    return {"success": True, "message": "Deconnecte"}


@router.get("/me")
async def get_me(user: TokenData = Depends(get_current_user)):
    """
    Retourne les informations de l'utilisateur connecte.
    Route protegee - necessite un token valide.
    """
    return {
        "user": user.sub,
        "authenticated": True,
        "token_issued_at": user.iat.isoformat(),
        "token_expires_at": user.exp.isoformat(),
    }


@router.post("/refresh")
async def refresh_token(user: TokenData = Depends(get_current_user)):
    """
    Rafraichit le token JWT.
    Retourne un nouveau token avec une nouvelle date d'expiration.
    """
    new_token = create_access_token(subject=user.sub)
    return {"success": True, "token": new_token}
