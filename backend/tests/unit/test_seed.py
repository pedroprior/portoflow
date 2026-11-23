"""O seed cumpre o mínimo do enunciado e os usuários criados conseguem entrar."""

from sqlalchemy import func, select

from app.models import Container, Escala, Janela, Usuario
from seed import popular


def _contar(db, modelo, *filtros):
    return db.scalar(select(func.count()).select_from(modelo).where(*filtros))


def test_seed_cria_o_minimo_e_e_idempotente(db):
    assert popular(db, "admin-senha-1", "padrao-senha-1") is True
    assert popular(db, "admin-senha-1", "padrao-senha-1") is False  # segunda vez não duplica

    assert _contar(db, Usuario, Usuario.papel == "admin") >= 1
    assert _contar(db, Escala) >= 3
    assert _contar(db, Container) >= 15
    assert _contar(db, Janela) > 0


def test_usuarios_do_seed_fazem_login(client, db):
    popular(db, "admin-senha-1", "padrao-senha-1")
    for usuario in db.scalars(select(Usuario)).all():
        senha = "admin-senha-1" if usuario.papel == "admin" else "padrao-senha-1"
        r = client.post("/auth/login", json={"email": usuario.email, "senha": senha})
        assert r.status_code == 200, (usuario.email, r.text)
