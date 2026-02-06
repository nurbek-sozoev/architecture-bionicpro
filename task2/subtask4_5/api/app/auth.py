from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx

from app.config import settings

security = HTTPBearer()

_jwks_cache: Optional[dict] = None


async def get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    
    jwks_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


def get_public_key_from_jwks(jwks: dict, kid: str) -> Optional[dict]:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


class TokenUser:
    def __init__(self, sub: str, username: str, email: Optional[str], client_id: Optional[int], roles: list[str]):
        self.sub = sub
        self.username = username
        self.email = email
        self.client_id = client_id
        self.roles = roles
    
    def is_admin(self) -> bool:
        return "admin" in self.roles


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenUser:
    token = credentials.credentials
    
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header missing kid",
            )
        
        jwks = await get_jwks()
        public_key = get_public_key_from_jwks(jwks, kid)
        
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Public key not found",
            )
        
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="account",
            options={"verify_aud": False}
        )
        
        sub = payload.get("sub")
        username = payload.get("preferred_username", "")
        email = payload.get("email")
        
        client_id_value = payload.get("client_id")
        client_id = None
        if client_id_value is not None:
            try:
                client_id = int(client_id_value)
            except (ValueError, TypeError):
                pass
        
        realm_access = payload.get("realm_access", {})
        roles = realm_access.get("roles", [])
        
        return TokenUser(
            sub=sub,
            username=username,
            email=email,
            client_id=client_id,
            roles=roles
        )
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not verify token: {str(e)}",
        )
