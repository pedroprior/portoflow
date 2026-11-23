from datetime import datetime, timezone


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def como_utc(valor: datetime) -> datetime:
    """Garante datetime com fuso. Bancos sem fuso (SQLite nos testes) devolvem datetimes ingênuos."""
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)
