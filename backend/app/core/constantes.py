from enum import StrEnum


class Papel(StrEnum):
    ADMIN = "admin"
    OPERADOR = "operador"
    EXTERNO = "externo"


class StatusUsuario(StrEnum):
    PENDENTE = "pendente"
    ATIVO = "ativo"
    INATIVO = "inativo"


class StatusEscala(StrEnum):
    PREVISTA = "prevista"
    ATRACADA = "atracada"
    ENCERRADA = "encerrada"


class StatusContainer(StrEnum):
    AGUARDANDO = "aguardando_chegada"
    NO_PATIO = "no_patio"
    SAIU = "saiu"


class TipoContainer(StrEnum):
    DRY = "dry"
    REEFER = "reefer"


class TipoMovimentacao(StrEnum):
    GATE_IN = "gate_in"
    GATE_OUT = "gate_out"
    REMOCAO = "remocao"


class Operacao(StrEnum):
    ENTREGA = "entrega"
    RETIRADA = "retirada"


class StatusAgendamento(StrEnum):
    CONFIRMADO = "confirmado"
    CUMPRIDO = "cumprido"
    CANCELADO = "cancelado"


TRANSICOES_AGENDAMENTO: dict[str, set[str]] = {
    StatusAgendamento.CONFIRMADO: {StatusAgendamento.CUMPRIDO, StatusAgendamento.CANCELADO},
    StatusAgendamento.CUMPRIDO: set(),
    StatusAgendamento.CANCELADO: set(),
}

TRANSICOES_ESCALA: dict[str, set[str]] = {
    StatusEscala.PREVISTA: {StatusEscala.ATRACADA},
    StatusEscala.ATRACADA: {StatusEscala.ENCERRADA},
    StatusEscala.ENCERRADA: set(),
}

TAMANHOS_CONTAINER = (20, 40)
ALTURA_MAXIMA = 5
CONTAINERS_POR_CAMINHAO = 2


def lista_sql(enum_cls) -> str:
    """Valores de um enum no formato usado em CHECK (... IN (...))."""
    return ", ".join(f"'{v.value}'" for v in enum_cls)
