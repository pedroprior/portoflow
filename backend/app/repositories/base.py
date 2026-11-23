import math
from typing import TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import nao_encontrado

M = TypeVar("M")


def obter_ou_404(db: Session, modelo: type[M], id_: int, nome: str) -> M:
    obj = db.get(modelo, id_)
    if obj is None or getattr(obj, "ativo", True) is False:
        raise nao_encontrado(f"{nome} não encontrado(a)")
    return obj


def paginar(db: Session, consulta: Select, pagina: int, tamanho: int) -> dict:
    """Executa a consulta paginada e devolve o dicionário no formato de Pagina."""
    total = db.scalar(select(func.count()).select_from(consulta.order_by(None).subquery())) or 0
    itens = db.scalars(consulta.offset((pagina - 1) * tamanho).limit(tamanho)).unique().all()
    return {
        "itens": itens,
        "total": total,
        "pagina": pagina,
        "tamanho_pagina": tamanho,
        "total_paginas": max(1, math.ceil(total / tamanho)),
    }
