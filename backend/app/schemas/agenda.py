from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constantes import CONTAINERS_POR_CAMINHAO, Operacao, StatusAgendamento
from app.schemas.comum import Placa, Saida
from app.schemas.containers import ContainerSaida, PosicaoSaida


class JanelaEntrada(BaseModel):
    inicio: datetime
    fim: datetime
    vagas_total: int = Field(gt=0, le=500)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"inicio": "2026-12-01T08:00:00Z", "fim": "2026-12-01T09:00:00Z", "vagas_total": 10}
            ]
        }
    )

    @model_validator(mode="after")
    def _fim_depois_inicio(self):
        if self.fim <= self.inicio:
            raise ValueError("fim deve ser depois do início")
        return self


class JanelaAtualizar(BaseModel):
    inicio: datetime | None = None
    fim: datetime | None = None
    vagas_total: int | None = Field(default=None, gt=0, le=500)


class JanelaSaida(Saida):
    id: int
    inicio: datetime
    fim: datetime
    vagas_total: int
    vagas_livres: int


class AgendamentoEntrada(BaseModel):
    janela_id: int
    operacao: Operacao
    container_ids: list[int] = Field(min_length=1, max_length=CONTAINERS_POR_CAMINHAO)
    placa: Placa
    motorista: str = Field(min_length=2, max_length=120)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "janela_id": 1,
                    "operacao": "retirada",
                    "container_ids": [3, 4],
                    "placa": "ABC1D23",
                    "motorista": "João Pereira",
                }
            ]
        }
    )

    @field_validator("container_ids")
    @classmethod
    def _sem_repetidos(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("containers repetidos")
        return v


class AgendamentoStatusEntrada(BaseModel):
    status: Literal["cancelado"] = Field(
        description="Só o cancelamento é feito à mão; 'cumprido' é registrado pelo portão"
    )


class AgendamentoSaida(Saida):
    id: int
    numero: str
    janela: JanelaSaida
    usuario_id: int
    operacao: Operacao
    placa: str
    motorista: str
    status: StatusAgendamento
    criado_em: datetime | None
    containers: list[ContainerSaida]


class Pendencia(BaseModel):
    codigo: str
    mensagem: str


class ItemConsultaPortao(BaseModel):
    container: ContainerSaida
    operacao: Operacao | None = Field(description="O que o portão deve fazer com este container")
    pendencias: list[Pendencia]
    posicao_sugerida: PosicaoSaida | None
    pode_registrar: bool


class AgendamentoResumo(Saida):
    id: int
    numero: str
    operacao: Operacao
    placa: str
    motorista: str
    status: StatusAgendamento
    janela: JanelaSaida


class ConsultaPortaoSaida(BaseModel):
    agendamento: AgendamentoResumo | None
    itens: list[ItemConsultaPortao]


class PortaoEntrada(BaseModel):
    codigo_container: str
    placa: Placa
    justificativa: str | None = Field(
        default=None, max_length=255, description="Obrigatória se a placa for diferente da agendada"
    )
    posicao_id: int | None = Field(
        default=None, description="Só no gate-in. Vazio: o sistema sugere a posição livre"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"codigo_container": "CSQU3054383", "placa": "ABC1D23"}]
        }
    )
