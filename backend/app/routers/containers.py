from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constantes import StatusContainer
from app.core.database import get_db
from app.core.deps import equipe_terminal, get_usuario_atual, so_admin, so_operador
from app.models import Usuario
from app.schemas.comum import Erro, Pagina
from app.schemas.containers import (
    BloqueioEntrada,
    BloqueioSaida,
    ContainerAtualizar,
    ContainerDetalhe,
    ContainerEntrada,
    ContainerSaida,
    MovimentacaoEntrada,
    PosicaoLivreSaida,
)
from app.services import containers as servico
from app.services import patio

router = APIRouter(tags=["Containers e pátio"])


@router.get(
    "/containers",
    response_model=Pagina[ContainerSaida],
    summary="Listar containers com busca, filtros e paginação",
    description="O usuário externo só recebe containers do próprio cliente.",
)
def listar(
    busca: str | None = Query(default=None, max_length=11, description="Parte do código"),
    status_: StatusContainer | None = Query(default=None, alias="status"),
    escala: int | None = None,
    cliente: int | None = None,
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=10, ge=1, le=100),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    return servico.listar(db, usuario, busca, status_, escala, cliente, pagina, tamanho_pagina)


@router.get(
    "/containers/{container_id}",
    response_model=ContainerDetalhe,
    summary="Detalhe do container com posição, bloqueios e histórico (UC07)",
    responses={404: {"model": Erro}},
)
def obter(container_id: int, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    return servico.obter(db, usuario, container_id)


@router.post(
    "/containers",
    response_model=ContainerSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar container (UC02)",
    responses={409: {"model": Erro}, 422: {"model": Erro}},
)
def criar(dados: ContainerEntrada, _: Usuario = Depends(equipe_terminal), db: Session = Depends(get_db)):
    return servico.criar(db, dados)


@router.put("/containers/{container_id}", response_model=ContainerSaida, summary="Editar container")
def atualizar(
    container_id: int,
    dados: ContainerAtualizar,
    _: Usuario = Depends(equipe_terminal),
    db: Session = Depends(get_db),
):
    return servico.atualizar(db, container_id, dados)


@router.delete(
    "/containers/{container_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativar container (soft delete)",
)
def desativar(container_id: int, _: Usuario = Depends(equipe_terminal), db: Session = Depends(get_db)):
    servico.desativar(db, container_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/containers/{container_id}/bloqueios",
    response_model=BloqueioSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Bloquear container (UC06); cancela retiradas agendadas",
)
def bloquear(
    container_id: int,
    dados: BloqueioEntrada,
    admin: Usuario = Depends(so_admin),
    db: Session = Depends(get_db),
):
    return servico.bloquear(db, admin, container_id, dados.motivo)


@router.delete(
    "/containers/{container_id}/bloqueios/{bloqueio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Liberar container (UC06)",
)
def liberar(
    container_id: int,
    bloqueio_id: int,
    admin: Usuario = Depends(so_admin),
    db: Session = Depends(get_db),
):
    servico.liberar(db, admin, container_id, bloqueio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/containers/{container_id}/movimentacoes",
    response_model=ContainerSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Movimentar container no pátio (UC05)",
    responses={409: {"model": Erro}},
)
def movimentar(
    container_id: int,
    dados: MovimentacaoEntrada,
    operador: Usuario = Depends(so_operador),
    db: Session = Depends(get_db),
):
    return patio.movimentar(db, operador, container_id, dados.posicao_id)


@router.get(
    "/patio/posicoes",
    response_model=list[PosicaoLivreSaida],
    summary="Posições do pátio; livres=true traz só as que podem receber container",
)
def posicoes(
    livres: bool = False, _: Usuario = Depends(equipe_terminal), db: Session = Depends(get_db)
):
    return patio.listar_posicoes(db, somente_livres=livres)
