from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constantes import StatusContainer, TipoContainer, TipoMovimentacao
from app.schemas.comum import Saida


class PosicaoSaida(Saida):
    id: int
    bloco: str
    fileira: int
    pilha: int
    altura: int
    endereco: str


class OcupanteSaida(BaseModel):
    id: int
    codigo: str
    bloqueado: bool
    tamanho: int


class PosicaoLivreSaida(PosicaoSaida):
    ocupada: bool
    container: OcupanteSaida | None = None


class ContainerEntrada(BaseModel):
    codigo: str = Field(description="Código ISO 6346, ex.: CSQU3054383")
    tamanho: Literal[20, 40]
    tipo: TipoContainer
    peso_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    cheio: bool
    perigoso: bool = False
    cliente_id: int
    escala_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "codigo": "CSQU3054383",
                    "tamanho": 20,
                    "tipo": "dry",
                    "peso_kg": "12500.00",
                    "cheio": True,
                    "perigoso": False,
                    "cliente_id": 1,
                    "escala_id": 1,
                }
            ]
        }
    )


class ContainerAtualizar(BaseModel):
    tamanho: Literal[20, 40] | None = None
    tipo: TipoContainer | None = None
    peso_kg: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    cheio: bool | None = None
    perigoso: bool | None = None
    escala_id: int | None = None


class ContainerSaida(Saida):
    id: int
    codigo: str
    tamanho: int
    tipo: TipoContainer
    peso_kg: Decimal
    cheio: bool
    perigoso: bool
    status: StatusContainer
    bloqueado: bool
    cliente_id: int
    escala_id: int
    posicao: PosicaoSaida | None


class MovimentacaoSaida(Saida):
    id: int
    tipo: TipoMovimentacao
    origem: PosicaoSaida | None
    destino: PosicaoSaida | None
    usuario_id: int
    observacao: str | None
    criado_em: datetime | None


class BloqueioSaida(Saida):
    id: int
    motivo: str
    criado_por: int
    criado_em: datetime | None
    liberado_por: int | None
    liberado_em: datetime | None


class EscalaResumo(Saida):
    id: int
    viagem: str
    status: str
    navio_nome: str


class ContainerDetalhe(ContainerSaida):
    escala: EscalaResumo
    bloqueios: list[BloqueioSaida]
    movimentacoes: list[MovimentacaoSaida]


class BloqueioEntrada(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"motivo": "Pendência documental: BL não apresentado"}]}
    )


class MovimentacaoEntrada(BaseModel):
    posicao_id: int = Field(description="Posição de destino no pátio")
