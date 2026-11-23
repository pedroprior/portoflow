"""Gate-in e gate-out: tudo ou nada."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.errors import ErroAPI
from app.models import Movimentacao
from app.schemas.agenda import AgendamentoEntrada, PortaoEntrada
from app.services import agenda, containers, portao


@pytest.fixture
def cenario(db, fab, externo):
    """Pátio vazio, janela agora e um container agendado para entrega."""
    posicoes = fab.posicoes()
    janela = fab.janela()
    c = fab.container(cliente=externo.cliente)
    ag = agenda.criar_agendamento(
        db,
        externo,
        AgendamentoEntrada(
            janela_id=janela.id, operacao="entrega", container_ids=[c.id], placa="ABC1D23", motorista="João"
        ),
    )
    return {"container": c, "agendamento": ag, "janela": janela, "posicoes": posicoes}


def _entrada(container, placa="ABC1D23", **extra):
    return PortaoEntrada(codigo_container=container.codigo, placa=placa, **extra)


def _movimentacoes(db):
    return db.scalar(select(func.count()).select_from(Movimentacao))


def test_gate_in_poe_no_patio_grava_historico_e_cumpre_agendamento(db, operador, cenario):
    c, ag = cenario["container"], cenario["agendamento"]

    resultado = portao.registrar_entrada(db, operador, _entrada(c))

    assert resultado.status == "no_patio"
    assert resultado.posicao.endereco == "A-01-01-1"
    db.refresh(ag)
    assert ag.status == "cumprido"
    mov = db.query(Movimentacao).filter_by(container_id=c.id).one()
    assert (mov.tipo, mov.destino_id, mov.usuario_id) == ("gate_in", resultado.posicao_id, operador.id)


def test_gate_in_fora_da_janela_nao_grava_nada(db, operador, cenario):
    c, janela = cenario["container"], cenario["janela"]
    depois = janela.fim + timedelta(hours=2)

    with pytest.raises(ErroAPI) as erro:
        portao.registrar_entrada(db, operador, _entrada(c), agora=depois)

    assert (erro.value.status, erro.value.codigo) == (409, "fora_da_janela")
    db.rollback()
    db.refresh(c)
    assert c.status == "aguardando_chegada"
    assert c.posicao_id is None
    assert _movimentacoes(db) == 0


def test_gate_in_sem_agendamento_e_recusado(db, fab, operador):
    fab.posicoes()
    c = fab.container()
    with pytest.raises(ErroAPI) as erro:
        portao.registrar_entrada(db, operador, _entrada(c))
    assert erro.value.codigo == "sem_agendamento"


def test_placa_diferente_exige_justificativa(db, operador, cenario):
    c = cenario["container"]
    with pytest.raises(ErroAPI) as erro:
        portao.registrar_entrada(db, operador, _entrada(c, placa="XYZ9876"))
    assert (erro.value.status, erro.value.codigo) == (400, "placa_divergente")

    resultado = portao.registrar_entrada(
        db, operador, _entrada(c, placa="XYZ9876", justificativa="Troca de cavalo mecânico")
    )
    assert resultado.status == "no_patio"
    mov = db.query(Movimentacao).filter_by(container_id=c.id).one()
    assert mov.observacao == "Troca de cavalo mecânico"


def test_gate_in_em_posicao_ocupada_nao_grava_nada(db, fab, operador, cenario):
    c = cenario["container"]
    ocupada = cenario["posicoes"][0]
    fab.container(status="no_patio", posicao=ocupada)
    with pytest.raises(ErroAPI) as erro:
        portao.registrar_entrada(db, operador, _entrada(c, posicao_id=ocupada.id))
    assert erro.value.codigo == "posicao_ocupada"
    db.rollback()
    db.refresh(c)
    assert c.status == "aguardando_chegada"


def test_agendamento_com_dois_containers_so_cumpre_no_segundo(db, fab, externo, operador):
    fab.posicoes()
    janela = fab.janela()
    c1 = fab.container(cliente=externo.cliente)
    c2 = fab.container(cliente=externo.cliente)
    ag = agenda.criar_agendamento(
        db,
        externo,
        AgendamentoEntrada(
            janela_id=janela.id, operacao="entrega", container_ids=[c1.id, c2.id], placa="ABC1D23", motorista="João"
        ),
    )

    portao.registrar_entrada(db, operador, _entrada(c1))
    db.refresh(ag)
    assert ag.status == "confirmado"

    portao.registrar_entrada(db, operador, _entrada(c2))
    db.refresh(ag)
    assert ag.status == "cumprido"


def _no_patio_com_retirada(db, fab, externo, posicao):
    janela = fab.janela()
    c = fab.container(cliente=externo.cliente, status="no_patio", posicao=posicao)
    agenda.criar_agendamento(
        db,
        externo,
        AgendamentoEntrada(
            janela_id=janela.id, operacao="retirada", container_ids=[c.id], placa="ABC1D23", motorista="João"
        ),
    )
    return c


def test_gate_out_libera_a_posicao(db, fab, externo, operador):
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    c = _no_patio_com_retirada(db, fab, externo, pos)

    resultado = portao.registrar_saida(db, operador, _entrada(c))

    assert resultado.status == "saiu"
    assert resultado.posicao_id is None
    mov = db.query(Movimentacao).filter_by(container_id=c.id).one()
    assert (mov.tipo, mov.origem_id) == ("gate_out", pos.id)


def test_gate_out_de_container_bloqueado_e_negado(db, fab, externo, operador, admin):
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    c = _no_patio_com_retirada(db, fab, externo, pos)
    c.bloqueado = True  # bloqueio feito direto no banco: o portão confere mesmo assim
    db.commit()

    with pytest.raises(ErroAPI) as erro:
        portao.registrar_saida(db, operador, _entrada(c))
    assert erro.value.codigo == "container_bloqueado"


def test_gate_out_com_container_em_cima_e_negado(db, fab, externo, operador):
    posicoes = fab.posicoes(pilhas=1, alturas=2)
    c = _no_patio_com_retirada(db, fab, externo, posicoes[0])
    fab.container(status="no_patio", posicao=posicoes[1])

    with pytest.raises(ErroAPI) as erro:
        portao.registrar_saida(db, operador, _entrada(c))
    assert erro.value.codigo == "container_por_baixo"


def test_liberar_bloqueio_permite_nova_retirada(db, fab, externo, admin):
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    c = fab.container(cliente=externo.cliente, status="no_patio", posicao=pos)
    bloqueio = containers.bloquear(db, admin, c.id, "Pendência")
    containers.liberar(db, admin, c.id, bloqueio.id)

    db.refresh(c)
    assert not c.bloqueado
    with pytest.raises(ErroAPI) as erro:
        containers.liberar(db, admin, c.id, bloqueio.id)
    assert erro.value.codigo == "ja_liberado"
