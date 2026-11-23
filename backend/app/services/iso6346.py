"""Validação do código de container no padrão ISO 6346.

Formato: 3 letras do proprietário + 1 letra de categoria (U, J ou Z)
+ 6 dígitos de série + 1 dígito verificador. Ex.: CSQU3054383.
"""

import re
import string

PADRAO = re.compile(r"^[A-Z]{3}[UJZ]\d{7}$")


def _tabela_letras() -> dict[str, int]:
    # A=10, B=12, ..., pulando múltiplos de 11 (11, 22, 33).
    valores, valor = {}, 10
    for letra in string.ascii_uppercase:
        if valor % 11 == 0:
            valor += 1
        valores[letra] = valor
        valor += 1
    return valores


_VALORES = _tabela_letras()


def normalizar(codigo: str) -> str:
    return re.sub(r"[\s-]", "", codigo).upper()


def digito_verificador(primeiros_10: str) -> int:
    if not re.fullmatch(r"[A-Z]{4}\d{6}", primeiros_10):
        raise ValueError("esperados 4 letras e 6 dígitos")
    total = sum(
        (_VALORES[c] if c.isalpha() else int(c)) * (2**i) for i, c in enumerate(primeiros_10)
    )
    return total % 11 % 10


def codigo_valido(codigo: str) -> bool:
    codigo = normalizar(codigo)
    if not PADRAO.match(codigo):
        return False
    return digito_verificador(codigo[:10]) == int(codigo[10])


def completar(primeiros_10: str) -> str:
    """Acrescenta o dígito verificador (útil para o seed)."""
    return primeiros_10 + str(digito_verificador(primeiros_10))
