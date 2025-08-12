from fastapi import HTTPException, status, Request
import jwt
from config import get_jwt_settings
from cache import cache_service

# Пример структуры payload: {"sub": user_id, "is_admin": bool, "is_super_admin": bool}

def _get_token_from_request(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    # Пробуем достать из cookie
    token = request.cookies.get("access_token")
    if token:
        return token
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No Bearer token")

def _decode_token(token: str) -> dict:
    settings = get_jwt_settings()
    try:
        issuer = settings.get("issuer", "auth_service")
        verify_aud = settings.get("verify_audience", False)
        audience = settings.get("audience")
        auth_service_url = settings.get("auth_service_url", "http://localhost:8000")
        jwks_client = jwt.PyJWKClient(f"{auth_service_url}/auth/.well-known/jwks.json")
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        decode_kwargs = {
            "algorithms": ["RS256"],
            "issuer": issuer,
            "options": {"verify_aud": verify_aud},
        }
        if verify_aud and audience:
            decode_kwargs["audience"] = audience
        payload = jwt.decode(token, signing_key, **decode_kwargs)
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user_id(request: Request) -> int:
    token = _get_token_from_request(request)
    payload = _decode_token(token)
    # revoke check
    jti = payload.get("jti")
    if jti:
        revoked = await cache_service.get(f"revoked:jti:{jti}")
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user_id in token")
    return int(user_id)

async def get_admin_user_id(request: Request) -> int:
    token = _get_token_from_request(request)
    payload = _decode_token(token)
    # revoke check
    jti = payload.get("jti")
    if jti:
        revoked = await cache_service.get(f"revoked:jti:{jti}")
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    if not (payload.get("is_admin") or payload.get("is_super_admin")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not admin")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user_id in token")
    return int(user_id)

async def get_super_admin_user_id(request: Request) -> int:
    token = _get_token_from_request(request)
    payload = _decode_token(token)
    # revoke check
    jti = payload.get("jti")
    if jti:
        revoked = await cache_service.get(f"revoked:jti:{jti}")
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    if not payload.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not superadmin")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user_id in token")
    return int(user_id) 