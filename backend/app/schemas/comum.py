import re
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict

T = TypeVar("T")

PADRAO_PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")  # antiga (ABC1234) e Mercosul (ABC1D23)


def normalizar_placa(valor: str) -> str:
    placa = valor.replace("-", "").replace(" ", "").upper()
    if not PADRAO_PLACA.match(placa):
        raise ValueError("placa inválida (use ABC1234 ou ABC1D23)")
    return placa


Placa = Annotated[str, AfterValidator(normalizar_placa)]


class Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Pagina(BaseModel, Generic[T]):
    itens: list[T]
    total: int
    pagina: int
    tamanho_pagina: int
    total_paginas: int


class ErroCorpo(BaseModel):
    codigo: str
    mensagem: str
    detalhes: list[dict] | None = None


class Erro(BaseModel):
    erro: ErroCorpo
