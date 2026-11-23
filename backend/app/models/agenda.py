"""Agendamento de janelas: janela (mestre de vagas), agendamento (mestre) e
agendamento_container (detalhe, N:N entre agendamento e container)."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constantes import Operacao, StatusAgendamento, lista_sql
from app.core.database import Base
from app.models.cadastros import Usuario
from app.models.patio import Container

agendamento_container = Table(
    "agendamento_container",
    Base.metadata,
    Column(
        "agendamento_id",
        Integer,
        ForeignKey("agendamento.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "container_id",
        Integer,
        ForeignKey("container.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    ),
)


class Janela(Base):
    __tablename__ = "janela"
    __table_args__ = (
        CheckConstraint("fim > inicio", name="fim_depois_inicio"),
        CheckConstraint("vagas_total > 0", name="vagas_total"),
        CheckConstraint("vagas_livres >= 0 AND vagas_livres <= vagas_total", name="vagas_livres"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fim: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vagas_total: Mapped[int] = mapped_column(Integer)
    vagas_livres: Mapped[int] = mapped_column(Integer)


class Agendamento(Base):
    __tablename__ = "agendamento"
    __table_args__ = (
        CheckConstraint(f"operacao IN ({lista_sql(Operacao)})", name="operacao"),
        CheckConstraint(f"status IN ({lista_sql(StatusAgendamento)})", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(12), unique=True)
    janela_id: Mapped[int] = mapped_column(ForeignKey("janela.id", ondelete="RESTRICT"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"), index=True)
    operacao: Mapped[str] = mapped_column(String(10))
    placa: Mapped[str] = mapped_column(String(7))
    motorista: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(12), default=StatusAgendamento.CONFIRMADO)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    janela: Mapped[Janela] = relationship()
    usuario: Mapped[Usuario] = relationship()
    containers: Mapped[list[Container]] = relationship(secondary=agendamento_container)
