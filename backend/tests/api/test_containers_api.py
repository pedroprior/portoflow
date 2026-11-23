import pytest


@pytest.fixture
def base(fab):
    return {"cliente": fab.cliente(), "escala": fab.escala()}


def _novo(base, codigo="CSQU3054383", **extra):
    return {
        "codigo": codigo,
        "tamanho": 20,
        "tipo": "dry",
        "peso_kg": "12500.50",
        "cheio": True,
        "cliente_id": base["cliente"].id,
        "escala_id": base["escala"].id,
        **extra,
    }


def test_operador_cadastra_container(client, fab, operador, base):
    r = client.post("/containers", json=_novo(base, codigo="csqu 305438-3"), headers=fab.headers(operador))
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["codigo"] == "CSQU3054383"  # normalizado
    assert corpo["status"] == "aguardando_chegada"
    assert corpo["peso_kg"] == "12500.50"  # decimal exato, serializado como texto


def test_codigo_com_digito_errado_devolve_422(client, fab, operador, base):
    r = client.post("/containers", json=_novo(base, codigo="CSQU3054384"), headers=fab.headers(operador))
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "codigo_invalido"


def test_codigo_duplicado_devolve_409(client, fab, operador, base):
    h = fab.headers(operador)
    client.post("/containers", json=_novo(base), headers=h)
    r = client.post("/containers", json=_novo(base), headers=h)
    assert r.status_code == 409


def test_peso_negativo_e_validado_na_api(client, fab, operador, base):
    r = client.post("/containers", json=_novo(base, peso_kg="-5"), headers=fab.headers(operador))
    assert r.status_code == 422
    assert r.json()["erro"]["detalhes"][0]["campo"] == "peso_kg"


def test_escala_inexistente_devolve_422(client, fab, operador, base):
    r = client.post("/containers", json=_novo(base, escala_id=999), headers=fab.headers(operador))
    assert r.status_code == 422


def test_listagem_paginada(client, fab, operador, base):
    for _ in range(23):
        fab.container(cliente=base["cliente"], escala=base["escala"])
    h = fab.headers(operador)

    p1 = client.get("/containers?tamanho_pagina=10", headers=h).json()
    p3 = client.get("/containers?tamanho_pagina=10&pagina=3", headers=h).json()

    assert (p1["total"], p1["total_paginas"], len(p1["itens"])) == (23, 3, 10)
    assert len(p3["itens"]) == 3
    assert not {c["id"] for c in p1["itens"]} & {c["id"] for c in p3["itens"]}


def test_busca_por_parte_do_codigo_e_filtros(client, fab, operador, base):
    alvo = fab.container(cliente=base["cliente"], escala=base["escala"])
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    no_patio = fab.container(status="no_patio", posicao=pos)
    h = fab.headers(operador)

    busca = client.get(f"/containers?busca={alvo.codigo[-5:].lower()}", headers=h).json()
    assert [c["id"] for c in busca["itens"]] == [alvo.id]

    por_status = client.get("/containers?status=no_patio", headers=h).json()
    assert [c["id"] for c in por_status["itens"]] == [no_patio.id]

    por_escala = client.get(f"/containers?escala={base['escala'].id}", headers=h).json()
    assert [c["id"] for c in por_escala["itens"]] == [alvo.id]


def test_lista_vazia(client, fab, operador):
    r = client.get("/containers?busca=NADA", headers=fab.headers(operador)).json()
    assert r == {"itens": [], "total": 0, "pagina": 1, "tamanho_pagina": 10, "total_paginas": 1}


def test_externo_so_ve_containers_do_proprio_cliente(client, fab, externo):
    meu = fab.container(cliente=externo.cliente)
    alheio = fab.container()
    h = fab.headers(externo)

    # mesmo pedindo o filtro de outro cliente, a API força o cliente do usuário
    lista = client.get(f"/containers?cliente={alheio.cliente_id}", headers=h).json()
    assert [c["id"] for c in lista["itens"]] == [meu.id]

    assert client.get(f"/containers/{meu.id}", headers=h).status_code == 200
    assert client.get(f"/containers/{alheio.id}", headers=h).status_code == 404


def test_detalhe_traz_escala_bloqueios_e_historico(client, fab, admin):
    c = fab.container()
    h = fab.headers(admin)
    client.post(f"/containers/{c.id}/bloqueios", json={"motivo": "Inspeção"}, headers=h)

    d = client.get(f"/containers/{c.id}", headers=h).json()
    assert d["bloqueado"] is True
    assert d["escala"]["navio_nome"].startswith("Navio")
    assert d["bloqueios"][0]["motivo"] == "Inspeção"
    assert d["movimentacoes"] == []


def test_desativar_e_soft_delete(client, fab, operador, db):
    from app.models import Container

    c = fab.container()
    h = fab.headers(operador)
    assert client.delete(f"/containers/{c.id}", headers=h).status_code == 204
    assert client.get(f"/containers/{c.id}", headers=h).status_code == 404
    db.expire_all()
    assert db.get(Container, c.id).ativo is False  # continua no banco


def test_nao_desativa_container_no_patio(client, fab, operador):
    pos = fab.posicoes(pilhas=1, alturas=1)[0]
    c = fab.container(status="no_patio", posicao=pos)
    r = client.delete(f"/containers/{c.id}", headers=fab.headers(operador))
    assert r.status_code == 409


def test_bloquear_duas_vezes_devolve_409_e_motivo_vazio_422(client, fab, admin):
    c = fab.container()
    h = fab.headers(admin)
    assert client.post(f"/containers/{c.id}/bloqueios", json={"motivo": ""}, headers=h).status_code == 422
    assert client.post(f"/containers/{c.id}/bloqueios", json={"motivo": "Avaria"}, headers=h).status_code == 201
    assert client.post(f"/containers/{c.id}/bloqueios", json={"motivo": "Avaria"}, headers=h).status_code == 409


def test_posicoes_livres(client, fab, operador):
    posicoes = fab.posicoes(pilhas=1, alturas=2)
    fab.container(status="no_patio", posicao=posicoes[0])
    r = client.get("/patio/posicoes?livres=true", headers=fab.headers(operador)).json()
    assert [p["endereco"] for p in r] == ["A-01-01-2"]
