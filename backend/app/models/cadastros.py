"""Cadastros de base: cliente, usuário, navio e escala."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constantes import Papel, StatusEscala, StatusUsuario, lista_sql
from app.core.database import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    razao_social: Mapped[str] = mapped_column(String(150))
    cnpj: Mapped[str] = mapped_column(String(14), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(f"papel IN ({lista_sql(Papel)})", name="papel"),
        CheckConstraint(f"status IN ({lista_sql(StatusUsuario)})", name="status"),
        # Usuário externo sempre pertence a um cliente.
        CheckConstraint("papel <> 'externo' OR cliente_id IS NOT NULL", name="externo_com_cliente"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(100))
    papel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=StatusUsuario.ATIVO)
    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("cliente.id", ondelete="RESTRICT"), index=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cliente: Mapped[Cliente | None] = relationship()


class Navio(Base):
    __tablename__ = "navio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    imo: Mapped[str] = mapped_column(String(7), unique=True)
    armador: Mapped[str] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Escala(Base):
    __tablename__ = "escala"
    __table_args__ = (
        UniqueConstraint("navio_id", "viagem", name="uq_escala_navio_viagem"),
        CheckConstraint("etd > eta", name="etd_depois_eta"),
        CheckConstraint(f"status IN ({lista_sql(StatusEscala)})", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    navio_id: Mapped[int] = mapped_column(ForeignKey("navio.id", ondelete="RESTRICT"), index=True)
    viagem: Mapped[str] = mapped_column(String(20))
    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    etd: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ata: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default=StatusEscala.PREVISTA)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    navio: Mapped[Navio] = relationship()

    @property
    def navio_nome(self) -> str:
        return self.navio.nome
