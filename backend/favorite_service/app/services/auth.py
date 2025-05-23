from fastapi import HTTPException, status, Request
import jwt
from config import get_jwt_settings

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
    jwt_settings = get_jwt_settings()
    try:
        payload = jwt.decode(token, jwt_settings["secret_key"], algorithms=[jwt_settings["algorithm"]])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def get_current_user_id(request: Request) -> int:
    token = _get_token_from_request(request)
    payload = _decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user_id in token")
    return int(user_id)

def get_admin_user_id(request: Request) -> int:
    token = _get_token_from_request(request)
    payload = _decode_token(token)
    if not (payload.get("is_admin") or payload.get("is_super_admin")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not admin")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user_id in token")
    return int(user_id)

def get_super_admin_user_id(request: Request) -> int:
    token = _get_token_from_request(request)
    payload = _decode_token(token)
    if not payload.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not superadmin")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user_id in token")
    return int(user_id) 