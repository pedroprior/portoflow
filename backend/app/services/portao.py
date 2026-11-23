"""Portão: gate-in (UC04) e gate-out.

O gate-in é a operação transacional principal do sistema: confere agendamento,
janela e placa, ocupa a posição no pátio, grava a movimentação, muda o status
do container e cumpre o agendamento em uma única transação. Qualquer falha ->
409 (ou 400) e nada é gravado.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import Operacao, StatusAgendamento, StatusContainer, TipoMovimentacao
from app.core.errors import conflito, invalido, nao_encontrado, requisicao_ruim
from app.core.tempo import agora_utc, como_utc
from app.models import Agendamento, Container, Movimentacao, PosicaoPatio, Usuario
from app.repositories import containers as repo
from app.schemas.agenda import PortaoEntrada
from app.schemas.comum import PADRAO_PLACA
from app.services import iso6346, patio
from app.services.containers import motivo_bloqueio_atual


def _container(db: Session, codigo: str) -> Container:
    container = repo.por_codigo(db, iso6346.normalizar(codigo))
    if container is None:
        raise nao_encontrado("Container não encontrado")
    return container


def _agendamento_valido(
    db: Session, container: Container, operacao: str, dados: PortaoEntrada, agora: datetime
) -> Agendamento:
    agendamentos = repo.agendamentos_ativos(db, container.id, operacao)
    if not agendamentos:
        raise conflito("sem_agendamento", f"Não há agendamento de {operacao} confirmado para {container.codigo}")
    agendamento = agendamentos[0]
    janela = agendamento.janela
    if not (como_utc(janela.inicio) <= agora <= como_utc(janela.fim)):
        raise conflito(
            "fora_da_janela",
            f"Chegada fora da janela agendada ({como_utc(janela.inicio):%d/%m %H:%M}"
            f"–{como_utc(janela.fim):%H:%M} UTC)",
        )
    if dados.placa != agendamento.placa and not (dados.justificativa or "").strip():
        raise requisicao_ruim(
            "placa_divergente",
            f"Placa diferente da agendada ({agendamento.placa}); informe uma justificativa",
        )
    return agendamento


def _cumprir_se_completo(agendamento: Agendamento, status_final: str) -> None:
    if all(c.status == status_final for c in agendamento.containers):
        agendamento.status = StatusAgendamento.CUMPRIDO


def registrar_entrada(
    db: Session, operador: Usuario, dados: PortaoEntrada, agora: datetime | None = None
) -> Container:
    agora = como_utc(agora) if agora else agora_utc()
    container = _container(db, dados.codigo_container)
    if container.status != StatusContainer.AGUARDANDO:
        raise conflito("status_incompativel", "Container já entrou no terminal")
    agendamento = _agendamento_valido(db, container, Operacao.ENTREGA, dados, agora)

    if dados.posicao_id is not None:
        destino = db.get(PosicaoPatio, dados.posicao_id)
        if destino is None:
            raise nao_encontrado("Posição não encontrada")
        patio.validar_destino(db, destino)
    else:
        destino = patio.sugerir_posicao(db)
        if destino is None:
            raise conflito("patio_cheio", "Não há posição livre no pátio")

    container.posicao_id = destino.id
    container.status = StatusContainer.NO_PATIO
    db.add(
        Movimentacao(
            container_id=container.id,
            tipo=TipoMovimentacao.GATE_IN,
            destino_id=destino.id,
            usuario_id=operador.id,
            observacao=(dados.justificativa or None),
        )
    )
    _cumprir_se_completo(agendamento, StatusContainer.NO_PATIO)
    db.commit()
    db.refresh(container)
    return container


def registrar_saida(
    db: Session, operador: Usuario, dados: PortaoEntrada, agora: datetime | None = None
) -> Container:
    agora = como_utc(agora) if agora else agora_utc()
    container = _container(db, dados.codigo_container)
    if container.status != StatusContainer.NO_PATIO or container.posicao is None:
        raise conflito("status_incompativel", "Container não está no pátio")
    if container.bloqueado:
        raise conflito(
            "container_bloqueado",
            f"Saída negada: container bloqueado ({motivo_bloqueio_atual(container)})",
        )
    if patio.tem_container_acima(db, container.posicao):
        raise conflito("container_por_baixo", "Há outro container em cima; remova-o antes")
    agendamento = _agendamento_valido(db, container, Operacao.RETIRADA, dados, agora)

    origem_id = container.posicao_id
    container.posicao_id = None
    container.status = StatusContainer.SAIU
    db.add(
        Movimentacao(
            container_id=container.id,
            tipo=TipoMovimentacao.GATE_OUT,
            origem_id=origem_id,
            usuario_id=operador.id,
            observacao=(dados.justificativa or None),
        )
    )
    _cumprir_se_completo(agendamento, StatusContainer.SAIU)
    db.commit()
    db.refresh(container)
    return container


# --- consulta prévia (somente leitura) ------------------------------------


def _pendencias(
    db: Session, container: Container, operacao: str | None, agendamento: Agendamento | None, agora: datetime
) -> list[dict]:
    """Mesmas regras do gate-in/out, mas sem gravar: o operador vê o problema antes de confirmar."""
    if operacao is None:
        return [{"codigo": "ja_saiu", "mensagem": "Container já saiu do terminal"}]
    pendencias = []
    if agendamento is None or agendamento.operacao != operacao:
        pendencias.append(
            {"codigo": "sem_agendamento", "mensagem": f"Sem agendamento de {operacao} confirmado"}
        )
    else:
        janela = agendamento.janela
        inicio, fim = como_utc(janela.inicio), como_utc(janela.fim)
        if agora < inicio:
            pendencias.append({"codigo": "fora_da_janela", "mensagem": f"Chegou antes da janela ({inicio:%d/%m %H:%M} UTC)"})
        elif agora > fim:
            pendencias.append({"codigo": "fora_da_janela", "mensagem": f"Janela encerrada às {fim:%d/%m %H:%M} UTC"})
    if operacao == Operacao.RETIRADA:
        if container.bloqueado:
            pendencias.append(
                {"codigo": "container_bloqueado", "mensagem": f"Bloqueado: {motivo_bloqueio_atual(container)}"}
            )
        if container.posicao and patio.tem_container_acima(db, container.posicao):
            pendencias.append(
                {"codigo": "container_por_baixo", "mensagem": "Há outro container em cima; remova-o antes"}
            )
    return pendencias


def _operacao_esperada(container: Container) -> str | None:
    if container.status == StatusContainer.AGUARDANDO:
        return Operacao.ENTREGA
    if container.status == StatusContainer.NO_PATIO:
        return Operacao.RETIRADA
    return None


def _agendamento_por_placa(db: Session, placa: str, agora: datetime) -> Agendamento | None:
    candidatos = db.scalars(
        select(Agendamento).where(
            Agendamento.placa == placa, Agendamento.status == StatusAgendamento.CONFIRMADO
        )
    ).all()
    # Prefere a janela em andamento; senão, a mais próxima de agora.
    return min(
        candidatos,
        key=lambda a: (
            not (como_utc(a.janela.inicio) <= agora <= como_utc(a.janela.fim)),
            abs((como_utc(a.janela.inicio) - agora).total_seconds()),
        ),
        default=None,
    )


def consultar(db: Session, termo: str, agora: datetime | None = None) -> dict:
    """Busca por código do container, número do agendamento (AG...) ou placa do caminhão."""
    agora = como_utc(agora) if agora else agora_utc()
    chave = iso6346.normalizar(termo)
    agendamento: Agendamento | None = None

    if iso6346.PADRAO.match(chave):
        container = _container(db, chave)
        containers = [container]
        operacao = _operacao_esperada(container)
        ativos = repo.agendamentos_ativos(db, container.id, operacao) if operacao else []
        agendamento = ativos[0] if ativos else None
    elif chave.startswith("AG") and len(chave) == 10:
        agendamento = db.scalar(select(Agendamento).where(Agendamento.numero == chave))
        if agendamento is None:
            raise nao_encontrado("Agendamento não encontrado")
        containers = list(agendamento.containers)
    elif PADRAO_PLACA.match(chave):
        agendamento = _agendamento_por_placa(db, chave, agora)
        if agendamento is None:
            raise nao_encontrado(f"Nenhum agendamento confirmado para a placa {chave}")
        containers = list(agendamento.containers)
    else:
        raise invalido("termo_invalido", "Digite o código do container, o número do agendamento ou a placa")

    itens = []
    for c in containers:
        operacao = _operacao_esperada(c)
        pendencias = _pendencias(db, c, operacao, agendamento, agora)
        sugerida = None
        if operacao == Operacao.ENTREGA and not pendencias:
            sugerida = patio.sugerir_posicao(db)
            if sugerida is None:
                pendencias.append({"codigo": "patio_cheio", "mensagem": "Não há posição livre no pátio"})
        itens.append(
            {
                "container": c,
                "operacao": operacao,
                "pendencias": pendencias,
                "posicao_sugerida": sugerida,
                "pode_registrar": not pendencias,
            }
        )
    return {"agendamento": agendamento, "itens": itens}
