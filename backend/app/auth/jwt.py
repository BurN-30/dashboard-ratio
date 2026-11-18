"""
Gestion des JWT (JSON Web Tokens) pour l'authentification.
"""
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
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

    now = datetime.now(timezone.utc)
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


SUJET_SESSION_SYNC = "session-sync"
SUJET_DEPOT_CLE = "depot-cle"
ENTETE_DEPOT_CLE = "X-Depot-Cle"

# Sur la route de depot, l'absence de Bearer n'est pas une erreur en soi : la cle de depot
# peut suffire. Les deux schemas restent declares dans OpenAPI.
_bearer_facultatif = HTTPBearer(auto_error=False)
_cle_de_depot = APIKeyHeader(name=ENTETE_DEPOT_CLE, auto_error=False)


async def get_session_depositor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_facultatif),
    cle: Optional[str] = Depends(_cle_de_depot),
) -> TokenData:
    """
    Dependency de la seule route de depot de session (POST /scrapers/session/{tracker}) :
    accepte le jeton Bearer de l'interface, le jeton dedie SESSION_SYNC_TOKEN du poste qui
    renouvelle la session, ou l'en-tete X-Depot-Cle egal a SESSION_DEPOT_CLE (script
    utilisateur). Ni ce jeton ni cette cle ne sont des JWT : toute autre route passe par
    get_current_user, qui ne lit pas l'en-tete et refuse le jeton. Variable vide ou absente :
    le mode correspondant est desactive. Aucune valeur recue n'est journalisee.
    """
    reglages = get_settings()
    maintenant = datetime.now(timezone.utc)
    # Comparaisons a temps constant (valeurs recues du reseau)
    attendue = reglages.session_depot_cle
    if attendue and cle and hmac.compare_digest(cle.encode(), attendue.encode()):
        return TokenData(sub=SUJET_DEPOT_CLE, exp=maintenant, iat=maintenant)
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )
    attendu = reglages.session_sync_token
    if attendu and hmac.compare_digest(credentials.credentials.encode(), attendu.encode()):
        return TokenData(sub=SUJET_SESSION_SYNC, exp=maintenant, iat=maintenant)
    return verify_token(credentials.credentials)
