"""Pátio: posições, containers, movimentações e bloqueios."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constantes import (
    ALTURA_MAXIMA,
    StatusContainer,
    TipoContainer,
    TipoMovimentacao,
    lista_sql,
)
from app.core.database import Base
from app.models.cadastros import Cliente, Escala, Usuario


class PosicaoPatio(Base):
    __tablename__ = "posicao_patio"
    __table_args__ = (
        UniqueConstraint("bloco", "fileira", "pilha", "altura", name="uq_posicao_patio_endereco"),
        CheckConstraint(f"altura BETWEEN 1 AND {ALTURA_MAXIMA}", name="altura"),
        CheckConstraint("fileira > 0", name="fileira"),
        CheckConstraint("pilha > 0", name="pilha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bloco: Mapped[str] = mapped_column(String(5))
    fileira: Mapped[int] = mapped_column(Integer)
    pilha: Mapped[int] = mapped_column(Integer)
    altura: Mapped[int] = mapped_column(Integer)

    @property
    def endereco(self) -> str:
        return f"{self.bloco}-{self.fileira:02d}-{self.pilha:02d}-{self.altura}"


class Container(Base):
    __tablename__ = "container"
    __table_args__ = (
        CheckConstraint("peso_kg > 0", name="peso_positivo"),
        CheckConstraint("tamanho IN (20, 40)", name="tamanho"),
        CheckConstraint(f"tipo IN ({lista_sql(TipoContainer)})", name="tipo"),
        CheckConstraint(f"status IN ({lista_sql(StatusContainer)})", name="status"),
        # Código único só entre containers ativos (soft delete permite reaproveitar).
        Index(
            "uq_container_codigo_ativo",
            "codigo",
            unique=True,
            postgresql_where=text("ativo"),
            sqlite_where=text("ativo"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(11), index=True)
    tamanho: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(10))
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cheio: Mapped[bool] = mapped_column(Boolean)
    perigoso: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    status: Mapped[str] = mapped_column(String(20), default=StatusContainer.AGUARDANDO, index=True)
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    posicao_id: Mapped[int | None] = mapped_column(
        ForeignKey("posicao_patio.id", ondelete="RESTRICT"), unique=True
    )
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="RESTRICT"), index=True)
    escala_id: Mapped[int] = mapped_column(ForeignKey("escala.id", ondelete="RESTRICT"), index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    posicao: Mapped[PosicaoPatio | None] = relationship()
    cliente: Mapped[Cliente] = relationship()
    escala: Mapped[Escala] = relationship()
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(
        back_populates="container", order_by="Movimentacao.id"
    )
    bloqueios: Mapped[list["Bloqueio"]] = relationship(
        back_populates="container", order_by="Bloqueio.id"
    )


class Movimentacao(Base):
    """Histórico imutável: guarda origem e destino do momento da movimentação."""

    __tablename__ = "movimentacao"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({lista_sql(TipoMovimentacao)})", name="tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    container_id: Mapped[int] = mapped_column(
        ForeignKey("container.id", ondelete="RESTRICT"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(10))
    origem_id: Mapped[int | None] = mapped_column(ForeignKey("posicao_patio.id", ondelete="RESTRICT"))
    destino_id: Mapped[int | None] = mapped_column(ForeignKey("posicao_patio.id", ondelete="RESTRICT"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    observacao: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    container: Mapped[Container] = relationship(back_populates="movimentacoes")
    origem: Mapped[PosicaoPatio | None] = relationship(foreign_keys=[origem_id])
    destino: Mapped[PosicaoPatio | None] = relationship(foreign_keys=[destino_id])
    usuario: Mapped[Usuario] = relationship()


class Bloqueio(Base):
    __tablename__ = "bloqueio"

    id: Mapped[int] = mapped_column(primary_key=True)
    container_id: Mapped[int] = mapped_column(
        ForeignKey("container.id", ondelete="RESTRICT"), index=True
    )
    motivo: Mapped[str] = mapped_column(String(255))
    criado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    liberado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    liberado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    container: Mapped[Container] = relationship(back_populates="bloqueios")
