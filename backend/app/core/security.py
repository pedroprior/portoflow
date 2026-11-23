from datetime import timedelta

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.tempo import agora_utc


def hash_senha(senha: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(senha.encode("utf-8"), salt).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        return False


def criar_token(usuario_id: int, papel: str) -> str:
    cfg = get_settings()
    payload = {
        "sub": str(usuario_id),
        "papel": papel,
        "exp": agora_utc() + timedelta(minutes=cfg.jwt_expira_min),
    }
    return jwt.encode(payload, cfg.jwt_secret, algorithm=cfg.jwt_algoritmo)


def decodificar_token(token: str) -> dict | None:
    """Devolve o payload do token, ou None se for inválido ou expirado."""
    cfg = get_settings()
    try:
        return jwt.decode(token, cfg.jwt_secret, algorithms=[cfg.jwt_algoritmo])
    except jwt.PyJWTError:
        return None
