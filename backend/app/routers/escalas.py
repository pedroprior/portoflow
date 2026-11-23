from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constantes import StatusEscala
from app.core.database import get_db
from app.core.deps import get_usuario_atual, so_admin
from app.models import Usuario
from app.repositories.base import obter_ou_404
from app.models import Escala
from app.schemas.escalas import (
    EscalaAtualizar,
    EscalaEntrada,
    EscalaSaida,
    NavioAtualizar,
    NavioEntrada,
    NavioSaida,
)
from app.services import escalas as servico

router = APIRouter(tags=["Navios e escalas"])


@router.get("/navios", response_model=list[NavioSaida], summary="Listar navios")
def listar_navios(_: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    return servico.listar_navios(db)


@router.post("/navios", response_model=NavioSaida, status_code=status.HTTP_201_CREATED, summary="Cadastrar navio")
def criar_navio(dados: NavioEntrada, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    return servico.criar_navio(db, dados)


@router.put("/navios/{navio_id}", response_model=NavioSaida, summary="Editar navio")
def editar_navio(
    navio_id: int, dados: NavioAtualizar, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)
):
    return servico.atualizar_navio(db, navio_id, dados)


@router.delete("/navios/{navio_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desativar navio")
def desativar_navio(navio_id: int, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    servico.desativar_navio(db, navio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/escalas", response_model=list[EscalaSaida], summary="Listar escalas ativas")
def listar_escalas(
    status_: StatusEscala | None = Query(default=None, alias="status"),
    _: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    return servico.listar_escalas(db, status_)


@router.get("/escalas/{escala_id}", response_model=EscalaSaida, summary="Detalhe da escala")
def obter_escala(escala_id: int, _: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    return obter_ou_404(db, Escala, escala_id, "Escala")


@router.post(
    "/escalas",
    response_model=EscalaSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar escala de navio (UC01)",
)
def criar_escala(dados: EscalaEntrada, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    return servico.criar_escala(db, dados)


@router.put(
    "/escalas/{escala_id}",
    response_model=EscalaSaida,
    summary="Editar escala; status segue prevista → atracada → encerrada",
)
def editar_escala(
    escala_id: int, dados: EscalaAtualizar, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)
):
    return servico.atualizar_escala(db, escala_id, dados)


@router.delete("/escalas/{escala_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desativar escala")
def desativar_escala(escala_id: int, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    servico.desativar_escala(db, escala_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
