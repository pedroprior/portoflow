"""Fluxos completos pela API: agendar, entrar, movimentar, bloquear e sair."""


def _agendar(client, fab, externo, janela, ids, operacao):
    return client.post(
        "/agendamentos",
        json={
            "janela_id": janela.id,
            "operacao": operacao,
            "container_ids": ids,
            "placa": "abc-1d23",
            "motorista": "João Pereira",
        },
        headers=fab.headers(externo),
    )


def test_ciclo_completo_de_um_container(client, fab, externo, operador, admin):
    fab.posicoes(pilhas=2, alturas=2)
    janela = fab.janela(vagas=5)
    c = fab.container(cliente=externo.cliente)
    h_op, h_adm = fab.headers(operador), fab.headers(admin)

    # 1. externo agenda a entrega
    r = _agendar(client, fab, externo, janela, [c.id], "entrega")
    assert r.status_code == 201, r.text
    assert r.json()["placa"] == "ABC1D23"
    assert r.json()["janela"]["vagas_livres"] == 4

    # 2. operador registra o gate-in
    r = client.post("/portao/entradas", json={"codigo_container": c.codigo, "placa": "ABC1D23"}, headers=h_op)
    assert r.status_code == 201, r.text
    assert r.json()["posicao"]["endereco"] == "A-01-01-1"

    # 3. operador move o container para outra pilha
    livres = client.get("/patio/posicoes?livres=true", headers=h_op).json()
    destino = next(p for p in livres if p["pilha"] == 2)
    r = client.post(f"/containers/{c.id}/movimentacoes", json={"posicao_id": destino["id"]}, headers=h_op)
    assert r.status_code == 201
    assert r.json()["posicao"]["endereco"] == "A-01-02-1"

    # 4. admin bloqueia; retirada é negada
    bloqueio = client.post(f"/containers/{c.id}/bloqueios", json={"motivo": "BL pendente"}, headers=h_adm).json()
    r = _agendar(client, fab, externo, janela, [c.id], "retirada")
    assert r.status_code == 409
    assert "BL pendente" in r.json()["erro"]["mensagem"]

    # 5. admin libera; externo agenda a retirada; operador registra a saída
    assert client.delete(f"/containers/{c.id}/bloqueios/{bloqueio['id']}", headers=h_adm).status_code == 204
    assert _agendar(client, fab, externo, janela, [c.id], "retirada").status_code == 201
    r = client.post("/portao/saidas", json={"codigo_container": c.codigo, "placa": "ABC1D23"}, headers=h_op)
    assert r.status_code == 201
    assert r.json()["status"] == "saiu"

    # 6. histórico completo no detalhe
    detalhe = client.get(f"/containers/{c.id}", headers=fab.headers(externo)).json()
    assert [m["tipo"] for m in detalhe["movimentacoes"]] == ["gate_in", "remocao", "gate_out"]
    assert detalhe["bloqueios"][0]["liberado_em"] is not None

    # 7. os dois agendamentos aparecem como cumpridos para o cliente
    meus = client.get("/agendamentos/meus", headers=fab.headers(externo)).json()
    assert [a["status"] for a in meus["itens"]] == ["cumprido", "cumprido"]


def test_janela_lotada_pela_api_devolve_409_com_mensagem(client, fab, externo):
    janela = fab.janela(vagas=1, livres=0)
    c = fab.container(cliente=externo.cliente)
    r = _agendar(client, fab, externo, janela, [c.id], "entrega")
    assert r.status_code == 409
    assert r.json()["erro"] == {"codigo": "janela_lotada", "mensagem": "A janela não tem mais vagas; escolha outra"}
    meus = client.get("/agendamentos/meus", headers=fab.headers(externo)).json()
    assert meus["total"] == 0


def test_meus_agendamentos_so_do_proprio_cliente(client, fab, externo):
    janela = fab.janela()
    outro = fab.usuario()  # externo de outro cliente
    _agendar(client, fab, externo, janela, [fab.container(cliente=externo.cliente).id], "entrega")
    _agendar(client, fab, outro, janela, [fab.container(cliente=outro.cliente).id], "entrega")

    meus = client.get("/agendamentos/meus", headers=fab.headers(externo)).json()
    assert meus["total"] == 1
    assert meus["itens"][0]["usuario_id"] == externo.id


def test_externo_nao_cancela_agendamento_de_outro_cliente(client, fab, externo):
    janela = fab.janela()
    outro = fab.usuario()
    ag = _agendar(client, fab, outro, janela, [fab.container(cliente=outro.cliente).id], "entrega").json()

    r = client.patch(f"/agendamentos/{ag['id']}/status", json={"status": "cancelado"}, headers=fab.headers(externo))
    assert r.status_code == 404

    r = client.patch(f"/agendamentos/{ag['id']}/status", json={"status": "cancelado"}, headers=fab.headers(outro))
    assert r.status_code == 200
    assert r.json()["janela"]["vagas_livres"] == janela.vagas_total


def test_status_manual_so_aceita_cancelado(client, fab, admin):
    r = client.patch("/agendamentos/1/status", json={"status": "cumprido"}, headers=fab.headers(admin))
    assert r.status_code == 422


def test_admin_lista_agendamentos_com_filtro(client, fab, externo, admin):
    janela = fab.janela()
    a1 = _agendar(client, fab, externo, janela, [fab.container(cliente=externo.cliente).id], "entrega").json()
    _agendar(client, fab, externo, janela, [fab.container(cliente=externo.cliente).id], "entrega")
    client.patch(f"/agendamentos/{a1['id']}/status", json={"status": "cancelado"}, headers=fab.headers(admin))

    r = client.get("/agendamentos?status=cancelado", headers=fab.headers(admin)).json()
    assert [a["id"] for a in r["itens"]] == [a1["id"]]


def test_gate_in_sem_agendamento_pela_api(client, fab, operador):
    fab.posicoes()
    c = fab.container()
    r = client.post("/portao/entradas", json={"codigo_container": c.codigo, "placa": "ABC1234"},
                    headers=fab.headers(operador))
    assert r.status_code == 409
    assert r.json()["erro"]["codigo"] == "sem_agendamento"


def test_gate_in_de_container_inexistente_devolve_404(client, fab, operador):
    r = client.post("/portao/entradas", json={"codigo_container": "CSQU3054383", "placa": "ABC1234"},
                    headers=fab.headers(operador))
    assert r.status_code == 404
