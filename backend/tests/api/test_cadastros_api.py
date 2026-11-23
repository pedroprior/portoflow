"""CRUD de navios, escalas, janelas, usuários e clientes."""

from conftest import SENHA

ESCALA = {"viagem": "024s", "eta": "2026-12-01T08:00:00Z", "etd": "2026-12-02T20:00:00Z"}


def _navio(client, h, imo="9876543"):
    return client.post("/navios", json={"nome": "MSC Aurora", "imo": imo, "armador": "MSC"}, headers=h).json()


def test_crud_de_escala(client, fab, admin, externo):
    h = fab.headers(admin)
    navio = _navio(client, h)

    criada = client.post("/escalas", json={**ESCALA, "navio_id": navio["id"]}, headers=h)
    assert criada.status_code == 201
    escala = criada.json()
    assert (escala["viagem"], escala["status"], escala["navio"]["nome"]) == ("024S", "prevista", "MSC Aurora")

    # qualquer usuário logado consulta
    assert client.get("/escalas", headers=fab.headers(externo)).json()[0]["id"] == escala["id"]

    r = client.put(f"/escalas/{escala['id']}", json={"status": "atracada"}, headers=h)
    assert r.status_code == 200
    assert r.json()["ata"] is not None

    assert client.delete(f"/escalas/{escala['id']}", headers=h).status_code == 204
    assert client.get("/escalas", headers=h).json() == []
    assert client.get(f"/escalas/{escala['id']}", headers=h).status_code == 404


def test_escala_duplicada_devolve_409(client, fab, admin):
    h = fab.headers(admin)
    navio = _navio(client, h)
    client.post("/escalas", json={**ESCALA, "navio_id": navio["id"]}, headers=h)
    r = client.post("/escalas", json={**ESCALA, "viagem": "024S", "navio_id": navio["id"]}, headers=h)
    assert r.status_code == 409
    assert r.json()["erro"]["codigo"] == "escala_duplicada"


def test_escala_com_saida_antes_da_atracacao_devolve_422(client, fab, admin):
    h = fab.headers(admin)
    navio = _navio(client, h)
    r = client.post("/escalas", json={**ESCALA, "etd": "2026-11-30T00:00:00Z", "navio_id": navio["id"]}, headers=h)
    assert r.status_code == 422


def test_escala_nao_pula_de_prevista_para_encerrada(client, fab, admin):
    h = fab.headers(admin)
    navio = _navio(client, h)
    escala = client.post("/escalas", json={**ESCALA, "navio_id": navio["id"]}, headers=h).json()
    r = client.put(f"/escalas/{escala['id']}", json={"status": "encerrada"}, headers=h)
    assert r.status_code == 409


def test_escala_com_containers_ativos_nao_e_desativada(client, fab, admin):
    c = fab.container()
    r = client.delete(f"/escalas/{c.escala_id}", headers=fab.headers(admin))
    assert r.status_code == 409


def test_imo_duplicado_devolve_409(client, fab, admin):
    h = fab.headers(admin)
    _navio(client, h)
    r = client.post("/navios", json={"nome": "Outro", "imo": "9876543", "armador": "Maersk"}, headers=h)
    assert r.status_code == 409


def test_crud_de_janela(client, fab, admin, externo):
    h = fab.headers(admin)
    criada = client.post(
        "/janelas",
        json={"inicio": "2026-12-01T08:00:00Z", "fim": "2026-12-01T09:00:00Z", "vagas_total": 4},
        headers=h,
    )
    assert criada.status_code == 201
    janela = criada.json()
    assert janela["vagas_livres"] == 4

    do_dia = client.get("/janelas?data=2026-12-01", headers=fab.headers(externo)).json()
    assert [j["id"] for j in do_dia] == [janela["id"]]
    assert client.get("/janelas?data=2026-12-02", headers=h).json() == []

    assert client.put(f"/janelas/{janela['id']}", json={"vagas_total": 6}, headers=h).json()["vagas_livres"] == 6
    assert client.delete(f"/janelas/{janela['id']}", headers=h).status_code == 204


def test_janela_com_agendamento_nao_e_removida(client, fab, admin, externo):
    janela = fab.janela()
    c = fab.container(cliente=externo.cliente)
    client.post(
        "/agendamentos",
        json={"janela_id": janela.id, "operacao": "entrega", "container_ids": [c.id],
              "placa": "ABC1234", "motorista": "Maria"},
        headers=fab.headers(externo),
    )
    assert client.delete(f"/janelas/{janela.id}", headers=fab.headers(admin)).status_code == 409


def test_admin_cria_usuario_externo_e_operador(client, fab, admin):
    h = fab.headers(admin)
    cliente = client.post("/clientes", json={"razao_social": "Transp X", "cnpj": "11222333000144"}, headers=h).json()

    ext = client.post(
        "/usuarios",
        json={"nome": "Ext", "email": "ext@x.com", "senha": "senha1234", "papel": "externo", "cliente_id": cliente["id"]},
        headers=h,
    )
    assert ext.status_code == 201
    assert ext.json()["status"] == "ativo"

    sem_cliente = client.post(
        "/usuarios", json={"nome": "Ext2", "email": "e2@x.com", "senha": "senha1234", "papel": "externo"}, headers=h
    )
    assert sem_cliente.status_code == 422

    op = client.post(
        "/usuarios", json={"nome": "Op", "email": "op@x.com", "senha": "senha1234", "papel": "operador"}, headers=h
    )
    assert op.status_code == 201
    assert op.json()["cliente_id"] is None


def test_admin_nao_desativa_nem_rebaixa_a_si_mesmo(client, fab, admin):
    h = fab.headers(admin)
    assert client.delete(f"/usuarios/{admin.id}", headers=h).status_code == 400
    assert client.put(f"/usuarios/{admin.id}", json={"papel": "operador"}, headers=h).status_code == 400


def test_listar_usuarios_pendentes(client, fab, admin):
    pendente = fab.usuario(status="pendente")
    r = client.get("/usuarios?status=pendente", headers=fab.headers(admin)).json()
    assert [u["id"] for u in r] == [pendente.id]


def test_cnpj_de_cliente_duplicado_devolve_409(client, fab, admin):
    h = fab.headers(admin)
    client.post("/clientes", json={"razao_social": "Alfa Ltda", "cnpj": "11222333000144"}, headers=h)
    r = client.post("/clientes", json={"razao_social": "Beta Ltda", "cnpj": "11.222.333/0001-44"}, headers=h)
    assert r.status_code == 409


def test_perfil_troca_nome_e_senha(client, fab, externo):
    h = fab.headers(externo)
    r = client.put("/usuarios/me", json={"senha_atual": "errada", "nova_senha": "novaSenha123"}, headers=h)
    assert r.status_code == 400

    r = client.put(
        "/usuarios/me", json={"nome": "Nome Novo", "senha_atual": SENHA, "nova_senha": "novaSenha123"}, headers=h
    )
    assert r.status_code == 200
    assert r.json()["nome"] == "Nome Novo"
    login = client.post("/auth/login", json={"email": externo.email, "senha": "novaSenha123"})
    assert login.status_code == 200
