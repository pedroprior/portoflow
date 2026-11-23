import pytest

from app.core.errors import ErroAPI
from app.models import Movimentacao
from app.services import patio


def _por_endereco(posicoes, pilha, altura):
    return next(p for p in posicoes if p.pilha == pilha and p.altura == altura)


def test_sugere_primeira_posicao_no_chao_com_patio_vazio(db, fab):
    fab.posicoes()
    assert patio.sugerir_posicao(db).endereco == "A-01-01-1"


def test_prefere_chao_livre_a_empilhar(db, fab):
    posicoes = fab.posicoes()  # 2 pilhas
    fab.container(status="no_patio", posicao=_por_endereco(posicoes, 1, 1))
    assert patio.sugerir_posicao(db).endereco == "A-01-02-1"


def test_empilha_quando_nao_ha_mais_chao(db, fab):
    posicoes = fab.posicoes()
    fab.container(status="no_patio", posicao=_por_endereco(posicoes, 1, 1))
    fab.container(status="no_patio", posicao=_por_endereco(posicoes, 2, 1))
    assert patio.sugerir_posicao(db).endereco == "A-01-01-2"


def test_sem_posicao_livre_devolve_none(db, fab):
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    fab.container(status="no_patio", posicao=pos)
    assert patio.sugerir_posicao(db) is None


def test_listar_livres_esconde_ocupadas_e_sem_apoio(db, fab):
    posicoes = fab.posicoes(pilhas=1, alturas=3)
    fab.container(status="no_patio", posicao=_por_endereco(posicoes, 1, 1))
    livres = [p["endereco"] for p in patio.listar_posicoes(db, somente_livres=True)]
    assert livres == ["A-01-01-2"]  # altura 1 ocupada; altura 3 não tem apoio


def test_destino_sem_apoio_e_recusado(db, fab):
    posicoes = fab.posicoes()
    with pytest.raises(ErroAPI) as erro:
        patio.validar_destino(db, _por_endereco(posicoes, 1, 2))
    assert erro.value.codigo == "sem_apoio"


def test_destino_ocupado_e_recusado(db, fab):
    posicoes = fab.posicoes()
    fab.container(status="no_patio", posicao=posicoes[0])
    with pytest.raises(ErroAPI) as erro:
        patio.validar_destino(db, posicoes[0])
    assert erro.value.status == 409
    assert erro.value.codigo == "posicao_ocupada"


def test_movimentar_grava_historico_com_origem_e_destino(db, fab, operador):
    posicoes = fab.posicoes()
    origem, destino = _por_endereco(posicoes, 1, 1), _por_endereco(posicoes, 2, 1)
    c = fab.container(status="no_patio", posicao=origem)

    patio.movimentar(db, operador, c.id, destino.id)

    db.refresh(c)
    assert c.posicao_id == destino.id
    mov = db.query(Movimentacao).filter_by(container_id=c.id).one()
    assert (mov.tipo, mov.origem_id, mov.destino_id, mov.usuario_id) == (
        "remocao", origem.id, destino.id, operador.id,
    )


def test_nao_movimenta_container_que_tem_outro_em_cima(db, fab, operador):
    posicoes = fab.posicoes()
    de_baixo = fab.container(status="no_patio", posicao=_por_endereco(posicoes, 1, 1))
    fab.container(status="no_patio", posicao=_por_endereco(posicoes, 1, 2))
    with pytest.raises(ErroAPI) as erro:
        patio.movimentar(db, operador, de_baixo.id, _por_endereco(posicoes, 2, 1).id)
    assert erro.value.codigo == "container_por_baixo"


def test_nao_empilha_sobre_si_mesmo(db, fab, operador):
    posicoes = fab.posicoes()
    c = fab.container(status="no_patio", posicao=_por_endereco(posicoes, 1, 1))
    with pytest.raises(ErroAPI) as erro:
        patio.movimentar(db, operador, c.id, _por_endereco(posicoes, 1, 2).id)
    assert erro.value.codigo == "sem_apoio"


def test_nao_movimenta_container_fora_do_patio(db, fab, operador):
    posicoes = fab.posicoes()
    c = fab.container()  # aguardando chegada
    with pytest.raises(ErroAPI) as erro:
        patio.movimentar(db, operador, c.id, posicoes[0].id)
    assert erro.value.codigo == "fora_do_patio"
