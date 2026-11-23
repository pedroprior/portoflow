from conftest import SENHA


def _registro(cnpj, email="novo@transp.com", senha="senhaForte1"):
    return {"nome": "Nova Pessoa", "email": email, "senha": senha, "cnpj": cnpj}


def test_registro_cria_externo_pendente_sem_expor_senha(client, fab):
    cliente = fab.cliente()
    r = client.post("/auth/registro", json=_registro(cliente.cnpj))
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["papel"] == "externo"
    assert corpo["status"] == "pendente"
    assert corpo["cliente_id"] == cliente.id
    assert "senha" not in corpo and "senha_hash" not in corpo


def test_registro_com_email_repetido_devolve_409(client, fab):
    cliente = fab.cliente()
    fab.usuario(email="repetido@teste.com")
    r = client.post("/auth/registro", json=_registro(cliente.cnpj, email="Repetido@Teste.com"))
    assert r.status_code == 409
    assert r.json()["erro"]["codigo"] == "email_duplicado"


def test_registro_com_cnpj_desconhecido_devolve_422(client):
    r = client.post("/auth/registro", json=_registro("11.111.111/0001-11"))
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "cnpj_desconhecido"


def test_registro_com_dados_invalidos_lista_os_campos(client):
    r = client.post("/auth/registro", json={"nome": "A", "email": "nao-e-email", "senha": "1", "cnpj": "1"})
    assert r.status_code == 422
    campos = {d["campo"] for d in r.json()["erro"]["detalhes"]}
    assert {"nome", "email", "senha", "cnpj"} <= campos


def test_login_devolve_jwt(client, admin):
    r = client.post("/auth/login", json={"email": admin.email.upper(), "senha": SENHA})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["papel"] == "admin"
    assert corpo["access_token"].count(".") == 2


def test_login_com_senha_errada_devolve_401(client, admin):
    r = client.post("/auth/login", json={"email": admin.email, "senha": "errada"})
    assert r.status_code == 401


def test_login_de_email_inexistente_tem_a_mesma_mensagem(client, admin):
    r1 = client.post("/auth/login", json={"email": admin.email, "senha": "errada"})
    r2 = client.post("/auth/login", json={"email": "ninguem@teste.com", "senha": "errada"})
    assert r1.json() == r2.json()  # não revela quais e-mails existem


def test_pendente_so_entra_depois_da_aprovacao(client, fab, admin):
    cliente = fab.cliente()
    novo = client.post("/auth/registro", json=_registro(cliente.cnpj)).json()

    r = client.post("/auth/login", json={"email": "novo@transp.com", "senha": "senhaForte1"})
    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "cadastro_pendente"

    aprovar = client.put(f"/usuarios/{novo['id']}", json={"status": "ativo"}, headers=fab.headers(admin))
    assert aprovar.status_code == 200

    r = client.post("/auth/login", json={"email": "novo@transp.com", "senha": "senhaForte1"})
    assert r.status_code == 200


def test_usuario_inativo_nao_entra(client, fab):
    u = fab.usuario(status="inativo")
    r = client.post("/auth/login", json={"email": u.email, "senha": SENHA})
    assert r.status_code == 403


def test_token_de_usuario_desativado_deixa_de_valer(client, fab, admin):
    u = fab.usuario()
    headers = fab.headers(u)
    assert client.get("/usuarios/me", headers=headers).status_code == 200
    client.delete(f"/usuarios/{u.id}", headers=fab.headers(admin))
    assert client.get("/usuarios/me", headers=headers).status_code == 401
