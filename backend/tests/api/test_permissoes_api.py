"""RF02: rotas administrativas devolvem 401 sem token e 403 para perfil sem permissão."""

import pytest

ROTAS_ADMIN = [
    ("get", "/usuarios"),
    ("post", "/usuarios"),
    ("put", "/usuarios/1"),
    ("delete", "/usuarios/1"),
    ("post", "/clientes"),
    ("post", "/navios"),
    ("post", "/escalas"),
    ("put", "/escalas/1"),
    ("delete", "/escalas/1"),
    ("post", "/janelas"),
    ("delete", "/janelas/1"),
    ("post", "/containers/1/bloqueios"),
    ("delete", "/containers/1/bloqueios/1"),
]

ROTAS_EQUIPE = [
    ("post", "/containers"),
    ("put", "/containers/1"),
    ("delete", "/containers/1"),
    ("get", "/agendamentos"),
    ("post", "/portao/entradas"),
    ("post", "/portao/saidas"),
    ("post", "/containers/1/movimentacoes"),
    ("get", "/patio/posicoes"),
]


def _chamar(client, metodo, rota, headers=None):
    kwargs = {"headers": headers or {}}
    if metodo in ("post", "put", "patch"):
        kwargs["json"] = {}
    return getattr(client, metodo)(rota, **kwargs)


@pytest.mark.parametrize("metodo, rota", ROTAS_ADMIN + ROTAS_EQUIPE + [("get", "/containers")])
def test_sem_token_devolve_401(client, metodo, rota):
    r = _chamar(client, metodo, rota)
    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "nao_autenticado"


@pytest.mark.parametrize("metodo, rota", ROTAS_ADMIN + ROTAS_EQUIPE)
def test_externo_devolve_403(client, fab, externo, metodo, rota):
    r = _chamar(client, metodo, rota, fab.headers(externo))
    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "proibido"


@pytest.mark.parametrize("metodo, rota", ROTAS_ADMIN)
def test_operador_devolve_403_nas_rotas_de_admin(client, fab, operador, metodo, rota):
    assert _chamar(client, metodo, rota, fab.headers(operador)).status_code == 403


@pytest.mark.parametrize("metodo, rota", [("post", "/agendamentos"), ("get", "/agendamentos/meus")])
def test_rotas_do_externo_negam_equipe_do_terminal(client, fab, admin, metodo, rota):
    assert _chamar(client, metodo, rota, fab.headers(admin)).status_code == 403


def test_token_invalido_devolve_401(client):
    r = client.get("/usuarios/me", headers={"Authorization": "Bearer nao.e.token"})
    assert r.status_code == 401


def test_rota_inexistente_tem_erro_no_formato_padrao(client):
    r = client.get("/nao-existe")
    assert r.status_code == 404
    assert set(r.json()["erro"]) >= {"codigo", "mensagem"}


def test_cors_so_libera_a_origem_do_front(client):
    ok = client.options(
        "/saude",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    negado = client.options(
        "/saude",
        headers={"Origin": "http://site-malicioso.com", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in negado.headers


def test_swagger_disponivel(client):
    assert client.get("/docs").status_code == 200
    esquema = client.get("/openapi.json").json()
    exemplo = esquema["components"]["schemas"]["ContainerEntrada"]["examples"][0]
    assert exemplo["codigo"] == "CSQU3054383"
