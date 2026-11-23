"""Pré-checagem do portão: mostra pendências antes de o operador confirmar."""

from datetime import timedelta

from app.core.tempo import agora_utc


def _agendar(client, fab, externo, janela, ids, operacao, placa="ABC1D23"):
    r = client.post(
        "/agendamentos",
        json={"janela_id": janela.id, "operacao": operacao, "container_ids": ids, "placa": placa, "motorista": "João"},
        headers=fab.headers(externo),
    )
    assert r.status_code == 201, r.text
    return r.json()


def _consultar(client, fab, operador, termo):
    return client.get("/portao/consulta", params={"termo": termo}, headers=fab.headers(operador))


def test_busca_pela_placa_traz_os_dois_containers_do_caminhao(client, fab, externo, operador):
    fab.posicoes()
    janela = fab.janela()
    c1, c2 = fab.container(cliente=externo.cliente), fab.container(cliente=externo.cliente)
    ag = _agendar(client, fab, externo, janela, [c1.id, c2.id], "entrega")

    r = _consultar(client, fab, operador, "abc-1d23")

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["agendamento"]["numero"] == ag["numero"]
    assert {i["container"]["codigo"] for i in corpo["itens"]} == {c1.codigo, c2.codigo}
    assert all(i["pode_registrar"] and i["operacao"] == "entrega" for i in corpo["itens"])
    assert corpo["itens"][0]["posicao_sugerida"]["endereco"] == "A-01-01-1"


def test_busca_pelo_numero_do_agendamento(client, fab, externo, operador):
    fab.posicoes()
    c = fab.container(cliente=externo.cliente)
    ag = _agendar(client, fab, externo, fab.janela(), [c.id], "entrega")
    r = _consultar(client, fab, operador, ag["numero"].lower())
    assert r.json()["itens"][0]["container"]["id"] == c.id


def test_container_sem_agendamento_mostra_pendencia(client, fab, operador):
    fab.posicoes()
    c = fab.container()
    item = _consultar(client, fab, operador, c.codigo).json()["itens"][0]
    assert item["pode_registrar"] is False
    assert [p["codigo"] for p in item["pendencias"]] == ["sem_agendamento"]


def test_container_bloqueado_mostra_motivo(client, fab, externo, operador, admin):
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    c = fab.container(cliente=externo.cliente, status="no_patio", posicao=pos)
    _agendar(client, fab, externo, fab.janela(), [c.id], "retirada")
    client.post(f"/containers/{c.id}/bloqueios", json={"motivo": "Vistoria da Receita"}, headers=fab.headers(admin))

    item = _consultar(client, fab, operador, c.codigo).json()["itens"][0]
    assert item["operacao"] == "retirada"
    codigos = [p["codigo"] for p in item["pendencias"]]
    # o bloqueio cancelou a retirada, então as duas pendências aparecem
    assert "container_bloqueado" in codigos and "sem_agendamento" in codigos
    assert any("Vistoria da Receita" in p["mensagem"] for p in item["pendencias"])


def test_janela_futura_aparece_como_antecipada(client, fab, externo, operador):
    fab.posicoes()
    c = fab.container(cliente=externo.cliente)
    futura = fab.janela(inicio=agora_utc() + timedelta(hours=3))
    _agendar(client, fab, externo, futura, [c.id], "entrega")
    item = _consultar(client, fab, operador, c.codigo).json()["itens"][0]
    assert item["pendencias"][0]["codigo"] == "fora_da_janela"
    assert "antes" in item["pendencias"][0]["mensagem"]


def test_consulta_nao_grava_nada(client, fab, externo, operador, db):
    from app.models import Movimentacao

    fab.posicoes()
    c = fab.container(cliente=externo.cliente)
    _agendar(client, fab, externo, fab.janela(), [c.id], "entrega")
    _consultar(client, fab, operador, c.codigo)
    db.expire_all()
    assert db.query(Movimentacao).count() == 0
    assert client.get(f"/containers/{c.id}", headers=fab.headers(operador)).json()["status"] == "aguardando_chegada"


def test_termo_invalido_e_inexistentes(client, fab, operador):
    assert _consultar(client, fab, operador, "xyz").status_code == 422
    assert _consultar(client, fab, operador, "CSQU3054383").status_code == 404
    assert _consultar(client, fab, operador, "ZZZ9Z99").status_code == 404
    assert _consultar(client, fab, operador, "AG00000000").status_code == 404


def test_externo_nao_usa_a_consulta_do_portao(client, fab, externo):
    assert _consultar(client, fab, externo, "ABC1D23").status_code == 403


def test_mapa_do_patio_mostra_ocupante(client, fab, operador):
    posicoes = fab.posicoes(pilhas=1, alturas=2)
    c = fab.container(status="no_patio", posicao=posicoes[0], bloqueado=True)
    mapa = client.get("/patio/posicoes", headers=fab.headers(operador)).json()
    assert mapa[0]["container"] == {"id": c.id, "codigo": c.codigo, "bloqueado": True, "tamanho": 20}
    assert mapa[1]["container"] is None
