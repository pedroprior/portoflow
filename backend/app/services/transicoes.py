from app.core.errors import conflito


def validar_transicao(atual: str, novo: str, mapa: dict[str, set[str]], entidade: str) -> None:
    if novo == atual:
        return
    if novo not in mapa.get(atual, set()):
        raise conflito(
            "transicao_invalida", f"{entidade}: não é possível passar de '{atual}' para '{novo}'"
        )
