"""
Gestion des JWT (JSON Web Tokens) pour l'authentification.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()
security = HTTPBearer()


class TokenData(BaseModel):
    """Donnees contenues dans le token."""
    sub: str  # Subject (identifiant utilisateur)
    exp: datetime  # Expiration
    iat: datetime  # Issued at


class TokenResponse(BaseModel):
    """Reponse lors de la creation d'un token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Secondes


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> TokenResponse:
    """
    Cree un JWT signe.

    Args:
        subject: Identifiant de l'utilisateur
        expires_delta: Duree de validite (defaut: settings.jwt_expire_hours)

    Returns:
        TokenResponse avec le token et les metadonnees
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.jwt_expire_hours)

    now = datetime.utcnow()
    expire = now + expires_delta

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": now,
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return TokenResponse(
        access_token=encoded_jwt,
        expires_in=int(expires_delta.total_seconds())
    )


def verify_token(token: str) -> TokenData:
    """
    Verifie et decode un JWT.

    Args:
        token: Le JWT a verifier

    Returns:
        TokenData avec les donnees du token

    Raises:
        HTTPException: Si le token est invalide ou expire
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expire",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception

        return TokenData(
            sub=sub,
            exp=datetime.fromtimestamp(payload.get("exp")),
            iat=datetime.fromtimestamp(payload.get("iat")),
        )

    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Dependency FastAPI pour extraire l'utilisateur du token.

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user": user.sub}
    """
    return verify_token(credentials.credentials)
