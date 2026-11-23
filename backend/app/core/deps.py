"""Dependências de autenticação e autorização por papel.

Sem token ou token inválido -> 401. Token válido com papel errado -> 403.
"""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.constantes import Papel, StatusUsuario
from app.core.database import get_db
from app.core.errors import nao_autenticado, proibido
from app.core.security import decodificar_token
from app.models import Usuario

_bearer = HTTPBearer(auto_error=False, description="Cole o token devolvido por POST /auth/login")


def get_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciais is None:
        raise nao_autenticado()
    payload = decodificar_token(credenciais.credentials)
    if payload is None or "sub" not in payload:
        raise nao_autenticado("Token inválido ou expirado")
    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or usuario.status != StatusUsuario.ATIVO:
        raise nao_autenticado("Usuário inexistente ou inativo")
    return usuario


def requer_papel(*papeis: Papel) -> Callable[..., Usuario]:
    def _verificar(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
        if usuario.papel not in papeis:
            raise proibido()
        return usuario

    return _verificar


so_admin = requer_papel(Papel.ADMIN)
equipe_terminal = requer_papel(Papel.ADMIN, Papel.OPERADOR)
so_externo = requer_papel(Papel.EXTERNO)
so_operador = requer_papel(Papel.OPERADOR, Papel.ADMIN)
