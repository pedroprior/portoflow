"""Regras de navios e escalas (UC01)."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.constantes import TRANSICOES_ESCALA, StatusEscala
from app.core.errors import conflito, invalido
from app.core.tempo import agora_utc, como_utc
from app.models import Container, Escala, Navio
from app.repositories.base import obter_ou_404
from app.schemas.escalas import EscalaAtualizar, EscalaEntrada, NavioAtualizar, NavioEntrada
from app.services.transicoes import validar_transicao

# --- navios ---------------------------------------------------------------


def listar_navios(db: Session) -> list[Navio]:
    return list(db.scalars(select(Navio).where(Navio.ativo.is_(True)).order_by(Navio.nome)).all())


def criar_navio(db: Session, dados: NavioEntrada) -> Navio:
    if db.scalar(select(Navio.id).where(Navio.imo == dados.imo)):
        raise conflito("imo_duplicado", "Já existe um navio com este número IMO")
    navio = Navio(**dados.model_dump())
    db.add(navio)
    db.commit()
    return navio


def atualizar_navio(db: Session, navio_id: int, dados: NavioAtualizar) -> Navio:
    navio = obter_ou_404(db, Navio, navio_id, "Navio")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(navio, campo, valor)
    db.commit()
    return navio


def desativar_navio(db: Session, navio_id: int) -> None:
    navio = obter_ou_404(db, Navio, navio_id, "Navio")
    navio.ativo = False
    db.commit()


# --- escalas --------------------------------------------------------------


def listar_escalas(db: Session, status: str | None = None) -> list[Escala]:
    consulta = (
        select(Escala)
        .options(selectinload(Escala.navio))
        .where(Escala.ativo.is_(True))
        .order_by(Escala.eta)
    )
    if status:
        consulta = consulta.where(Escala.status == status)
    return list(db.scalars(consulta).all())


def _sem_duplicada(db: Session, navio_id: int, viagem: str, ignorar_id: int | None = None) -> None:
    consulta = select(Escala.id).where(Escala.navio_id == navio_id, Escala.viagem == viagem)
    if ignorar_id:
        consulta = consulta.where(Escala.id != ignorar_id)
    if db.scalar(consulta):
        raise conflito("escala_duplicada", "Já existe escala para este navio e viagem")


def criar_escala(db: Session, dados: EscalaEntrada) -> Escala:
    obter_ou_404(db, Navio, dados.navio_id, "Navio")
    viagem = dados.viagem.strip().upper()
    _sem_duplicada(db, dados.navio_id, viagem)
    escala = Escala(
        navio_id=dados.navio_id,
        viagem=viagem,
        eta=dados.eta,
        etd=dados.etd,
        status=StatusEscala.PREVISTA,
    )
    db.add(escala)
    db.commit()
    return escala


def atualizar_escala(db: Session, escala_id: int, dados: EscalaAtualizar) -> Escala:
    escala = obter_ou_404(db, Escala, escala_id, "Escala")
    campos = dados.model_dump(exclude_unset=True)
    if "viagem" in campos:
        campos["viagem"] = campos["viagem"].strip().upper()
        _sem_duplicada(db, escala.navio_id, campos["viagem"], escala.id)
    novo_status = campos.pop("status", None)
    for campo, valor in campos.items():
        setattr(escala, campo, valor)
    if como_utc(escala.etd) <= como_utc(escala.eta):
        raise invalido("datas_invalidas", "Previsão de saída deve ser depois da previsão de atracação")
    if novo_status:
        validar_transicao(escala.status, novo_status, TRANSICOES_ESCALA, "Escala")
        if novo_status == StatusEscala.ATRACADA and escala.status != novo_status:
            escala.ata = agora_utc()
        if novo_status == StatusEscala.ENCERRADA and escala.status != novo_status:
            escala.atd = agora_utc()
        escala.status = novo_status
    db.commit()
    return escala


def desativar_escala(db: Session, escala_id: int) -> None:
    escala = obter_ou_404(db, Escala, escala_id, "Escala")
    tem_container_ativo = db.scalar(
        select(Container.id).where(Container.escala_id == escala.id, Container.ativo.is_(True))
    )
    if tem_container_ativo:
        raise conflito("escala_em_uso", "Escala tem containers ativos vinculados")
    escala.ativo = False  # soft delete: preserva o histórico
    db.commit()
