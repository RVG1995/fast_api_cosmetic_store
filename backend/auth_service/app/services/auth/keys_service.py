"""Сервис управления ключами для RS256 и JWKS.

- Загружает приватный/публичный ключи из ENV или файлов
- При отсутствии — генерирует новый RSA-ключ (если доступен пакет cryptography)
- Публикует JWK и JWKS для верификации токенов в других сервисах
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from config import settings

logger = logging.getLogger(__name__)

_PRIVATE_KEY_PEM: Optional[bytes] = None
_PUBLIC_KEY_PEM: Optional[bytes] = None
_KID: Optional[str] = None
_JWK: Optional[Dict] = None

# Старые публичные ключи, которые остаются в JWKS до истечения токенов
# kid -> (public_pem, expires_at)
_OLD_PUBLIC_KEYS: Dict[str, Tuple[bytes, datetime]] = {}


def _b64url_uint(n: int) -> str:
    """Преобразует целое число в base64url без '=' по RFC7515."""
    width = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(width, "big")).rstrip(b"=").decode("ascii")


def _compute_kid_from_public_pem(public_pem: bytes) -> str:
    """Вычисляет kid как усеченный sha256 от публичного PEM (стабильно и просто)."""
    digest = hashlib.sha256(public_pem).hexdigest()
    return digest[:16]


def _load_keys_from_env_or_files() -> bool:
    global _PRIVATE_KEY_PEM, _PUBLIC_KEY_PEM

    # ENV c PEM содержимым
    priv_from_env = os.getenv("JWT_PRIVATE_KEY_PEM")
    pub_from_env = os.getenv("JWT_PUBLIC_KEY_PEM")
    if priv_from_env and pub_from_env:
        _PRIVATE_KEY_PEM = priv_from_env.encode()
        _PUBLIC_KEY_PEM = pub_from_env.encode()
        logger.info("RSA ключи загружены из переменных окружения")
        return True

    # Пути к файлам
    priv_path = os.getenv("JWT_PRIVATE_KEY_PATH")
    pub_path = os.getenv("JWT_PUBLIC_KEY_PATH")
    if priv_path and pub_path and os.path.exists(priv_path) and os.path.exists(pub_path):
        with open(priv_path, "rb") as f:
            _PRIVATE_KEY_PEM = f.read()
        with open(pub_path, "rb") as f:
            _PUBLIC_KEY_PEM = f.read()
        logger.info("RSA ключи загружены из файлов: %s, %s", priv_path, pub_path)
        return True

    return False


def _generate_keys_if_possible() -> bool:
    """Пробует сгенерировать RSA-ключи при наличии cryptography."""
    global _PRIVATE_KEY_PEM, _PUBLIC_KEY_PEM
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        _PRIVATE_KEY_PEM = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_key = key.public_key()
        _PUBLIC_KEY_PEM = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        logger.warning("RSA ключи сгенерированы автоматически для RS256. Используйте постоянные ключи в проде!")
        return True
    except Exception as exc:  # cryptography отсутствует или иная ошибка
        logger.error("Не удалось сгенерировать RSA ключи. Установите cryptography или задайте ключи через ENV/файлы: %s", exc)
        return False


def _build_jwk_from_public_pem(public_pem: bytes) -> Dict:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    public_key = serialization.load_pem_public_key(public_pem, backend=default_backend())
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("Ожидался RSA публичный ключ")

    numbers = public_key.public_numbers()
    n_b64 = _b64url_uint(numbers.n)
    e_b64 = _b64url_uint(numbers.e)

    kid = _compute_kid_from_public_pem(public_pem)
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": n_b64,
        "e": e_b64,
    }
    return jwk


def initialize_keys() -> None:
    """Инициализация ключей и JWK. Вызывается при старте приложения."""
    global _KID, _JWK

    if not _load_keys_from_env_or_files():
        if not _generate_keys_if_possible():
            # Последняя попытка: использовать симметричный HS256 как fallback запрещаем — требуется RS256
            raise RuntimeError(
                "RSA ключи не найдены и не удалось сгенерировать. Установите cryptography или задайте JWT_PRIVATE_KEY_PEM/JWT_PUBLIC_KEY_PEM"
            )

    _KID = _compute_kid_from_public_pem(_PUBLIC_KEY_PEM)  # type: ignore[arg-type]

    try:
        _JWK = _build_jwk_from_public_pem(_PUBLIC_KEY_PEM)  # type: ignore[arg-type]
    except Exception as exc:
        logger.error("Не удалось построить JWK: %s", exc)
        raise


def get_private_key_pem() -> bytes:
    if _PRIVATE_KEY_PEM is None:
        initialize_keys()
    return _PRIVATE_KEY_PEM  # type: ignore[return-value]


def get_public_key_pem() -> bytes:
    if _PUBLIC_KEY_PEM is None:
        initialize_keys()
    return _PUBLIC_KEY_PEM  # type: ignore[return-value]


def get_kid() -> str:
    if _KID is None:
        initialize_keys()
    return _KID  # type: ignore[return-value]


def get_jwk() -> Dict:
    if _JWK is None:
        initialize_keys()
    return _JWK  # type: ignore[return-value]


def get_jwks() -> Dict:
    # Чистим просроченные старые ключи
    now = datetime.now(timezone.utc)
    expired = [kid for kid, (_, exp) in _OLD_PUBLIC_KEYS.items() if exp <= now]
    for kid in expired:
        _OLD_PUBLIC_KEYS.pop(kid, None)

    keys = [get_jwk()]
    # Добавляем старые ключи (ещё валидные) в JWKS
    for kid, (pub_pem, _) in _OLD_PUBLIC_KEYS.items():
        try:
            jwk = _build_jwk_from_public_pem(pub_pem)
            # Принудительно выставляем исходный kid
            jwk["kid"] = kid
            keys.append(jwk)
        except Exception as exc:
            logger.warning("Ошибка построения JWK для старого ключа %s: %s", kid, exc)
            continue
    return {"keys": keys}


def rotate_keys(keep_seconds: Optional[int] = None) -> Tuple[str, Optional[datetime]]:
    """Ротирует активный RSA ключ.

    - Текущий публичный ключ переносится в пул старых ключей и остаётся
      в JWKS до `keep_seconds` (или до времени жизни refresh токена по умолчанию).
    - Создаётся новый ключ и становится активным; новые токены подписываются им.

    Returns: (new_kid, kept_until)
    """
    global _PRIVATE_KEY_PEM, _PUBLIC_KEY_PEM, _KID, _JWK

    if _PUBLIC_KEY_PEM is None or _PRIVATE_KEY_PEM is None:
        initialize_keys()

    # Определяем время хранения старого ключа
    if keep_seconds is None:
        keep_seconds = settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60
    kept_until = datetime.now(timezone.utc) + timedelta(seconds=keep_seconds)

    # Кладём текущий публичный ключ в старые
    if _PUBLIC_KEY_PEM and _KID:
        _OLD_PUBLIC_KEYS[_KID] = (_PUBLIC_KEY_PEM, kept_until)

    # Генерируем новый ключ
    if not _generate_keys_if_possible():
        raise RuntimeError("Не удалось сгенерировать новый RSA ключ при ротации")

    # Обновляем активные идентификаторы
    _KID = _compute_kid_from_public_pem(_PUBLIC_KEY_PEM)  # type: ignore[arg-type]
    _JWK = _build_jwk_from_public_pem(_PUBLIC_KEY_PEM)   # type: ignore[arg-type]

    logger.info("Ротация RSA ключа выполнена. Новый kid=%s. Старый ключ будет доступен до %s", _KID, kept_until)
    return _KID, kept_until


