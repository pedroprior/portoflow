from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.comum import Erro
from app.schemas.usuarios import LoginEntrada, RegistroEntrada, TokenSaida, UsuarioSaida
from app.services import usuarios as servico

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/registro",
    response_model=UsuarioSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Criar conta de usuário externo (fica pendente até o admin aprovar)",
    responses={409: {"model": Erro}, 422: {"model": Erro}},
)
def registrar(dados: RegistroEntrada, db: Session = Depends(get_db)):
    return servico.registrar(db, dados)


@router.post(
    "/login",
    response_model=TokenSaida,
    summary="Autenticar e receber o JWT",
    responses={401: {"model": Erro}, 403: {"model": Erro}},
)
def login(dados: LoginEntrada, db: Session = Depends(get_db)):
    token, usuario = servico.autenticar(db, dados)
    return TokenSaida(access_token=token, papel=usuario.papel, nome=usuario.nome)
