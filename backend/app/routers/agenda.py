from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constantes import StatusAgendamento
from app.core.database import get_db
from app.core.deps import equipe_terminal, get_usuario_atual, so_admin, so_externo, so_operador
from app.models import Usuario
from app.schemas.agenda import (
    AgendamentoEntrada,
    AgendamentoSaida,
    AgendamentoStatusEntrada,
    ConsultaPortaoSaida,
    JanelaAtualizar,
    JanelaEntrada,
    JanelaSaida,
    PortaoEntrada,
)
from app.schemas.comum import Erro, Pagina
from app.schemas.containers import ContainerSaida
from app.services import agenda as servico
from app.services import portao

router = APIRouter()


# --- janelas --------------------------------------------------------------


@router.get("/janelas", response_model=list[JanelaSaida], tags=["Janelas"], summary="Listar janelas")
def listar_janelas(
    data: date | None = Query(default=None, description="Dia (AAAA-MM-DD)"),
    com_vaga: bool = False,
    _: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    return servico.listar_janelas(db, data, com_vaga)


@router.post(
    "/janelas",
    response_model=JanelaSaida,
    status_code=status.HTTP_201_CREATED,
    tags=["Janelas"],
    summary="Criar janela de atendimento",
)
def criar_janela(dados: JanelaEntrada, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    return servico.criar_janela(db, dados)


@router.put("/janelas/{janela_id}", response_model=JanelaSaida, tags=["Janelas"], summary="Editar janela")
def editar_janela(
    janela_id: int, dados: JanelaAtualizar, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)
):
    return servico.atualizar_janela(db, janela_id, dados)


@router.delete(
    "/janelas/{janela_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Janelas"],
    summary="Remover janela sem agendamentos",
)
def remover_janela(janela_id: int, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    servico.remover_janela(db, janela_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- agendamentos ---------------------------------------------------------


@router.post(
    "/agendamentos",
    response_model=AgendamentoSaida,
    status_code=status.HTTP_201_CREATED,
    tags=["Agendamentos"],
    summary="Agendar entrega ou retirada (UC03) — transacional",
    responses={409: {"model": Erro, "description": "Janela lotada, container bloqueado etc."}},
)
def agendar(dados: AgendamentoEntrada, usuario: Usuario = Depends(so_externo), db: Session = Depends(get_db)):
    return servico.criar_agendamento(db, usuario, dados)


@router.get(
    "/agendamentos/meus",
    response_model=Pagina[AgendamentoSaida],
    tags=["Agendamentos"],
    summary="Agendamentos do meu cliente",
)
def meus_agendamentos(
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=10, ge=1, le=100),
    usuario: Usuario = Depends(so_externo),
    db: Session = Depends(get_db),
):
    return servico.listar_do_cliente(db, usuario, pagina, tamanho_pagina)


@router.get(
    "/agendamentos",
    response_model=Pagina[AgendamentoSaida],
    tags=["Agendamentos"],
    summary="Listar todos os agendamentos",
)
def listar_agendamentos(
    status_: StatusAgendamento | None = Query(default=None, alias="status"),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=10, ge=1, le=100),
    _: Usuario = Depends(equipe_terminal),
    db: Session = Depends(get_db),
):
    return servico.listar_todos(db, status_, pagina, tamanho_pagina)


@router.patch(
    "/agendamentos/{agendamento_id}/status",
    response_model=AgendamentoSaida,
    tags=["Agendamentos"],
    summary="Cancelar agendamento (devolve a vaga)",
)
def alterar_status(
    agendamento_id: int,
    dados: AgendamentoStatusEntrada,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    return servico.alterar_status(db, usuario, agendamento_id, dados.status)


# --- portão ---------------------------------------------------------------


@router.get(
    "/portao/consulta",
    response_model=ConsultaPortaoSaida,
    tags=["Portão"],
    summary="Pré-checagem do portão (não grava nada)",
    description="Aceita código do container, número do agendamento (AG...) ou placa. "
    "Devolve o que fazer com cada container e as pendências que impediriam a operação.",
    responses={404: {"model": Erro}, 422: {"model": Erro}},
)
def consulta_portao(
    termo: str = Query(min_length=3, max_length=20),
    _: Usuario = Depends(so_operador),
    db: Session = Depends(get_db),
):
    return portao.consultar(db, termo)


@router.post(
    "/portao/entradas",
    response_model=ContainerSaida,
    status_code=status.HTTP_201_CREATED,
    tags=["Portão"],
    summary="Gate-in (UC04) — transacional",
    responses={409: {"model": Erro}, 400: {"model": Erro}},
)
def gate_in(dados: PortaoEntrada, operador: Usuario = Depends(so_operador), db: Session = Depends(get_db)):
    return portao.registrar_entrada(db, operador, dados)


@router.post(
    "/portao/saidas",
    response_model=ContainerSaida,
    status_code=status.HTTP_201_CREATED,
    tags=["Portão"],
    summary="Gate-out — recusa container bloqueado",
    responses={409: {"model": Erro}, 400: {"model": Erro}},
)
def gate_out(dados: PortaoEntrada, operador: Usuario = Depends(so_operador), db: Session = Depends(get_db)):
    return portao.registrar_saida(db, operador, dados)
