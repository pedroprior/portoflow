"""As regras ficam também no próprio banco (CHECK, UNIQUE, FK), não só na API."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Container, Janela, PosicaoPatio, Usuario


def _commit_falha(db, obj):
    db.add(obj)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_peso_zero_e_recusado_pelo_banco(db, fab):
    c = fab.container()
    c.peso_kg = Decimal("0")
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_altura_acima_do_limite_e_recusada(db):
    _commit_falha(db, PosicaoPatio(bloco="A", fileira=1, pilha=1, altura=6))


def test_endereco_de_posicao_e_unico(db, fab):
    fab.posicoes(pilhas=1, alturas=1)
    _commit_falha(db, PosicaoPatio(bloco="A", fileira=1, pilha=1, altura=1))


def test_vagas_livres_nao_passam_do_total(db, fab):
    janela = fab.janela(vagas=2)
    janela.vagas_livres = 3
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_vagas_livres_nao_ficam_negativas(db, fab):
    janela = fab.janela(vagas=2, livres=0)
    janela.vagas_livres = -1
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_usuario_externo_sem_cliente_e_recusado(db):
    _commit_falha(db, Usuario(nome="X", email="x@x.com", senha_hash="h", papel="externo", status="ativo"))


def test_papel_desconhecido_e_recusado(db):
    _commit_falha(db, Usuario(nome="X", email="x@x.com", senha_hash="h", papel="root", status="ativo"))


def test_email_unico(db, fab):
    fab.usuario(email="repetido@teste.com")
    _commit_falha(db, Usuario(nome="Y", email="repetido@teste.com", senha_hash="h", papel="admin", status="ativo"))


def test_dois_containers_nao_ocupam_a_mesma_posicao(db, fab):
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    fab.container(status="no_patio", posicao=pos)
    with pytest.raises(IntegrityError):
        fab.container(status="no_patio", posicao=pos)
    db.rollback()


def test_codigo_unico_so_entre_containers_ativos(db, fab):
    original = fab.container()
    copia = dict(
        codigo=original.codigo, tamanho=20, tipo="dry", peso_kg=Decimal("1"), cheio=True,
        status="aguardando_chegada", cliente_id=original.cliente_id, escala_id=original.escala_id,
    )
    _commit_falha(db, Container(**copia))

    original.ativo = False  # soft delete libera o código
    db.commit()
    db.add(Container(**copia))
    db.commit()
    assert len(db.scalars(select(Container).where(Container.codigo == original.codigo)).all()) == 2


def test_fk_impede_container_com_cliente_inexistente(db, fab):
    escala = fab.escala()
    _commit_falha(
        db,
        Container(codigo="CSQU3054383", tamanho=20, tipo="dry", peso_kg=Decimal("1"), cheio=True,
                  status="aguardando_chegada", cliente_id=9999, escala_id=escala.id),
    )


def test_janela_com_fim_antes_do_inicio_e_recusada(db, fab):
    janela = fab.janela()
    janela.fim = janela.inicio
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.get(Janela, janela.id) is not None
