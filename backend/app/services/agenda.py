"""Janelas e agendamentos (UC03).

Agendar é a operação equivalente a "baixa de estoque": a vaga da janela é
travada com SELECT ... FOR UPDATE, conferida e baixada na mesma transação que
grava o agendamento e seus itens. Sem vaga -> 409 e nada é gravado.
"""

import secrets
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.constantes import (
    TRANSICOES_AGENDAMENTO,
    Operacao,
    Papel,
    StatusAgendamento,
    StatusContainer,
)
from app.core.errors import conflito, invalido, nao_encontrado
from app.core.tempo import agora_utc, como_utc
from app.models import Agendamento, Container, Janela, Usuario
from app.repositories import containers as repo
from app.repositories.base import paginar
from app.schemas.agenda import AgendamentoEntrada, JanelaAtualizar, JanelaEntrada
from app.services.containers import motivo_bloqueio_atual
from app.services.transicoes import validar_transicao

# --- janelas --------------------------------------------------------------


def listar_janelas(db: Session, dia: date | None = None, somente_com_vaga: bool = False) -> list[Janela]:
    consulta = select(Janela).order_by(Janela.inicio)
    if dia:
        inicio = datetime.combine(dia, time.min, tzinfo=timezone.utc)
        consulta = consulta.where(Janela.inicio >= inicio, Janela.inicio < inicio + timedelta(days=1))
    if somente_com_vaga:
        consulta = consulta.where(Janela.vagas_livres > 0)
    return list(db.scalars(consulta).all())


def criar_janela(db: Session, dados: JanelaEntrada) -> Janela:
    janela = Janela(
        inicio=dados.inicio,
        fim=dados.fim,
        vagas_total=dados.vagas_total,
        vagas_livres=dados.vagas_total,
    )
    db.add(janela)
    db.commit()
    return janela


def _janela_travada(db: Session, janela_id: int) -> Janela:
    janela = db.scalar(select(Janela).where(Janela.id == janela_id).with_for_update())
    if janela is None:
        raise nao_encontrado("Janela não encontrada")
    return janela


def atualizar_janela(db: Session, janela_id: int, dados: JanelaAtualizar) -> Janela:
    janela = _janela_travada(db, janela_id)
    campos = dados.model_dump(exclude_unset=True)
    if "vagas_total" in campos:
        ocupadas = janela.vagas_total - janela.vagas_livres
        if campos["vagas_total"] < ocupadas:
            raise conflito(
                "vagas_insuficientes", f"A janela já tem {ocupadas} vaga(s) ocupada(s)"
            )
        janela.vagas_livres = campos["vagas_total"] - ocupadas
        janela.vagas_total = campos["vagas_total"]
    janela.inicio = campos.get("inicio", janela.inicio)
    janela.fim = campos.get("fim", janela.fim)
    if como_utc(janela.fim) <= como_utc(janela.inicio):
        raise invalido("datas_invalidas", "Fim deve ser depois do início")
    db.commit()
    return janela


def remover_janela(db: Session, janela_id: int) -> None:
    janela = _janela_travada(db, janela_id)
    if db.scalar(select(Agendamento.id).where(Agendamento.janela_id == janela.id)):
        raise conflito("janela_em_uso", "Janela tem agendamentos e não pode ser removida")
    db.delete(janela)
    db.commit()


# --- agendamentos ---------------------------------------------------------


def _gerar_numero(db: Session) -> str:
    while True:
        numero = "AG" + secrets.token_hex(4).upper()
        if not db.scalar(select(Agendamento.id).where(Agendamento.numero == numero)):
            return numero


def _validar_containers(db: Session, usuario: Usuario, dados: AgendamentoEntrada) -> list[Container]:
    containers = list(
        db.scalars(
            select(Container).where(Container.id.in_(dados.container_ids), Container.ativo.is_(True))
        ).all()
    )
    if len(containers) != len(dados.container_ids) or any(
        c.cliente_id != usuario.cliente_id for c in containers
    ):
        raise nao_encontrado("Container não encontrado")

    if len(containers) > 1 and any(c.tamanho != 20 for c in containers):
        raise invalido(
            "carga_do_caminhao", "Um caminhão leva até 2 containers de 20' ou 1 container de 40'"
        )

    for c in containers:
        if dados.operacao == Operacao.ENTREGA and c.status != StatusContainer.AGUARDANDO:
            raise conflito("status_incompativel", f"{c.codigo} não está aguardando chegada")
        if dados.operacao == Operacao.RETIRADA:
            if c.status != StatusContainer.NO_PATIO:
                raise conflito("status_incompativel", f"{c.codigo} não está no pátio")
            if c.bloqueado:
                raise conflito(
                    "container_bloqueado",
                    f"{c.codigo} está bloqueado: {motivo_bloqueio_atual(c)}",
                )
        if repo.agendamentos_ativos(db, c.id):
            raise conflito("agendamento_existente", f"{c.codigo} já tem agendamento confirmado")
    return containers


def criar_agendamento(
    db: Session, usuario: Usuario, dados: AgendamentoEntrada, agora: datetime | None = None
) -> Agendamento:
    agora = como_utc(agora) if agora else agora_utc()
    containers = _validar_containers(db, usuario, dados)

    janela = _janela_travada(db, dados.janela_id)
    if como_utc(janela.fim) <= agora:
        raise conflito("janela_encerrada", "Esta janela já terminou")
    if janela.vagas_livres <= 0:
        raise conflito("janela_lotada", "A janela não tem mais vagas; escolha outra")

    janela.vagas_livres -= 1
    agendamento = Agendamento(
        numero=_gerar_numero(db),
        janela=janela,
        usuario_id=usuario.id,
        operacao=dados.operacao,
        placa=dados.placa,
        motorista=dados.motorista.strip(),
        status=StatusAgendamento.CONFIRMADO,
        containers=containers,
    )
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)
    return agendamento


def _consulta_agendamentos():
    return (
        select(Agendamento)
        .options(selectinload(Agendamento.janela), selectinload(Agendamento.containers))
        .order_by(Agendamento.id.desc())
    )


def listar_do_cliente(db: Session, usuario: Usuario, pagina: int, tamanho: int) -> dict:
    """Agendamentos de todos os usuários do mesmo cliente do usuário externo."""
    consulta = (
        _consulta_agendamentos()
        .join(Usuario, Usuario.id == Agendamento.usuario_id)
        .where(Usuario.cliente_id == usuario.cliente_id)
    )
    return paginar(db, consulta, pagina, tamanho)


def listar_todos(db: Session, status: str | None, pagina: int, tamanho: int) -> dict:
    consulta = _consulta_agendamentos()
    if status:
        consulta = consulta.where(Agendamento.status == status)
    return paginar(db, consulta, pagina, tamanho)


def alterar_status(db: Session, usuario: Usuario, agendamento_id: int, novo: str) -> Agendamento:
    agendamento = db.get(Agendamento, agendamento_id)
    dono_ok = (
        usuario.papel != Papel.EXTERNO
        or (agendamento is not None and agendamento.usuario.cliente_id == usuario.cliente_id)
    )
    if agendamento is None or not dono_ok:
        raise nao_encontrado("Agendamento não encontrado")
    validar_transicao(agendamento.status, novo, TRANSICOES_AGENDAMENTO, "Agendamento")
    if novo == StatusAgendamento.CANCELADO and agendamento.status != novo:
        janela = _janela_travada(db, agendamento.janela_id)
        janela.vagas_livres += 1
    agendamento.status = novo
    db.commit()
    db.refresh(agendamento)
    return agendamento
