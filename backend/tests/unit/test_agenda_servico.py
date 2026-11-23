"""Agendar é a operação transacional equivalente à baixa de estoque."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.errors import ErroAPI
from app.core.tempo import agora_utc
from app.models import Agendamento
from app.schemas.agenda import AgendamentoEntrada
from app.services import agenda, containers


def _dados(janela, ids, operacao="entrega"):
    return AgendamentoEntrada(
        janela_id=janela.id, operacao=operacao, container_ids=ids, placa="ABC1D23", motorista="João"
    )


def _qtd_agendamentos(db):
    return db.scalar(select(func.count()).select_from(Agendamento))


def test_agendar_baixa_uma_vaga_e_vincula_containers(db, fab, externo):
    janela = fab.janela(vagas=3)
    c1 = fab.container(cliente=externo.cliente)
    c2 = fab.container(cliente=externo.cliente)

    ag = agenda.criar_agendamento(db, externo, _dados(janela, [c1.id, c2.id]))

    db.refresh(janela)
    assert janela.vagas_livres == 2
    assert ag.status == "confirmado"
    assert ag.numero.startswith("AG")
    assert {c.id for c in ag.containers} == {c1.id, c2.id}


def test_janela_lotada_devolve_409_e_nao_grava_nada(db, fab, externo):
    janela = fab.janela(vagas=1, livres=0)
    c = fab.container(cliente=externo.cliente)

    with pytest.raises(ErroAPI) as erro:
        agenda.criar_agendamento(db, externo, _dados(janela, [c.id]))

    assert (erro.value.status, erro.value.codigo) == (409, "janela_lotada")
    db.rollback()
    db.refresh(janela)
    assert janela.vagas_livres == 0
    assert _qtd_agendamentos(db) == 0


def test_ultima_vaga_so_pode_ser_usada_uma_vez(db, fab, externo):
    janela = fab.janela(vagas=1)
    c1 = fab.container(cliente=externo.cliente)
    c2 = fab.container(cliente=externo.cliente)

    agenda.criar_agendamento(db, externo, _dados(janela, [c1.id]))
    with pytest.raises(ErroAPI):
        agenda.criar_agendamento(db, externo, _dados(janela, [c2.id]))
    assert _qtd_agendamentos(db) == 1


def test_janela_encerrada_e_recusada(db, fab, externo):
    janela = fab.janela(inicio=agora_utc() - timedelta(hours=3))
    c = fab.container(cliente=externo.cliente)
    with pytest.raises(ErroAPI) as erro:
        agenda.criar_agendamento(db, externo, _dados(janela, [c.id]))
    assert erro.value.codigo == "janela_encerrada"


def test_caminhao_nao_leva_dois_containers_de_40(db, fab, externo):
    janela = fab.janela()
    c1 = fab.container(cliente=externo.cliente, tamanho=40)
    c2 = fab.container(cliente=externo.cliente, tamanho=20)
    with pytest.raises(ErroAPI) as erro:
        agenda.criar_agendamento(db, externo, _dados(janela, [c1.id, c2.id]))
    assert (erro.value.status, erro.value.codigo) == (422, "carga_do_caminhao")


def test_container_de_outro_cliente_aparece_como_inexistente(db, fab, externo):
    janela = fab.janela()
    alheio = fab.container()  # outro cliente
    with pytest.raises(ErroAPI) as erro:
        agenda.criar_agendamento(db, externo, _dados(janela, [alheio.id]))
    assert erro.value.status == 404


def test_retirada_de_container_bloqueado_e_recusada_com_motivo(db, fab, externo, admin):
    janela = fab.janela()
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    c = fab.container(cliente=externo.cliente, status="no_patio", posicao=pos)
    containers.bloquear(db, admin, c.id, "Pendência documental")

    with pytest.raises(ErroAPI) as erro:
        agenda.criar_agendamento(db, externo, _dados(janela, [c.id], "retirada"))
    assert erro.value.codigo == "container_bloqueado"
    assert "Pendência documental" in erro.value.mensagem


def test_entrega_exige_container_aguardando_chegada(db, fab, externo):
    janela = fab.janela()
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    c = fab.container(cliente=externo.cliente, status="no_patio", posicao=pos)
    with pytest.raises(ErroAPI) as erro:
        agenda.criar_agendamento(db, externo, _dados(janela, [c.id], "entrega"))
    assert erro.value.codigo == "status_incompativel"


def test_container_nao_tem_dois_agendamentos_confirmados(db, fab, externo):
    janela = fab.janela()
    c = fab.container(cliente=externo.cliente)
    agenda.criar_agendamento(db, externo, _dados(janela, [c.id]))
    with pytest.raises(ErroAPI) as erro:
        agenda.criar_agendamento(db, externo, _dados(janela, [c.id]))
    assert erro.value.codigo == "agendamento_existente"


def test_cancelar_devolve_a_vaga(db, fab, externo):
    janela = fab.janela(vagas=2)
    c = fab.container(cliente=externo.cliente)
    ag = agenda.criar_agendamento(db, externo, _dados(janela, [c.id]))

    agenda.alterar_status(db, externo, ag.id, "cancelado")

    db.refresh(janela)
    assert janela.vagas_livres == 2
    with pytest.raises(ErroAPI):  # cancelado é final
        agenda.alterar_status(db, externo, ag.id, "cumprido")


def test_bloquear_cancela_retiradas_e_devolve_vagas(db, fab, externo, admin):
    janela = fab.janela(vagas=2)
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    c = fab.container(cliente=externo.cliente, status="no_patio", posicao=pos)
    ag = agenda.criar_agendamento(db, externo, _dados(janela, [c.id], "retirada"))

    containers.bloquear(db, admin, c.id, "Inspeção da Receita")

    db.refresh(ag)
    db.refresh(janela)
    assert ag.status == "cancelado"
    assert janela.vagas_livres == 2


def test_reduzir_vagas_abaixo_das_ocupadas_e_recusado(db, fab, externo):
    from app.schemas.agenda import JanelaAtualizar

    janela = fab.janela(vagas=3)
    for _ in range(2):
        c = fab.container(cliente=externo.cliente)
        agenda.criar_agendamento(db, externo, _dados(janela, [c.id]))

    with pytest.raises(ErroAPI) as erro:
        agenda.atualizar_janela(db, janela.id, JanelaAtualizar(vagas_total=1))
    assert erro.value.codigo == "vagas_insuficientes"

    agenda.atualizar_janela(db, janela.id, JanelaAtualizar(vagas_total=5))
    db.refresh(janela)
    assert (janela.vagas_total, janela.vagas_livres) == (5, 3)
