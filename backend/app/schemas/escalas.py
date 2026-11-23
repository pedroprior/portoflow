from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constantes import StatusEscala
from app.schemas.comum import Saida


class NavioEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    imo: str = Field(pattern=r"^\d{7}$", description="Número IMO, 7 dígitos")
    armador: str = Field(min_length=2, max_length=120)

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"nome": "MSC Aurora", "imo": "9876543", "armador": "MSC"}]}
    )


class NavioAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    armador: str | None = Field(default=None, min_length=2, max_length=120)
    ativo: bool | None = None


class NavioSaida(Saida):
    id: int
    nome: str
    imo: str
    armador: str
    ativo: bool


class EscalaEntrada(BaseModel):
    navio_id: int
    viagem: str = Field(min_length=1, max_length=20)
    eta: datetime = Field(description="Previsão de atracação")
    etd: datetime = Field(description="Previsão de saída")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "navio_id": 1,
                    "viagem": "024S",
                    "eta": "2026-12-01T08:00:00Z",
                    "etd": "2026-12-02T20:00:00Z",
                }
            ]
        }
    )

    @model_validator(mode="after")
    def _etd_depois_eta(self):
        if self.etd <= self.eta:
            raise ValueError("previsão de saída deve ser depois da previsão de atracação")
        return self


class EscalaAtualizar(BaseModel):
    viagem: str | None = Field(default=None, min_length=1, max_length=20)
    eta: datetime | None = None
    etd: datetime | None = None
    status: StatusEscala | None = None


class EscalaSaida(Saida):
    id: int
    navio_id: int
    navio: NavioSaida
    viagem: str
    eta: datetime
    etd: datetime
    ata: datetime | None
    atd: datetime | None
    status: StatusEscala
    ativo: bool
