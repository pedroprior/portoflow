"""Fixtures compartilhadas.

Os testes usam SQLite em memória (um banco novo por teste), com chaves
estrangeiras ligadas, para rodar sem Docker. As constraints CHECK, UNIQUE e FK
do modelo também valem no SQLite.
"""

import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "segredo-so-para-testes"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["CORS_ORIGEM"] = "http://localhost:5173"

from datetime import datetime, timedelta, timezone  # noqa: E402
from decimal import Decimal  # noqa: E402
from itertools import count  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.constantes import Papel, StatusContainer, StatusUsuario  # noqa: E402
from app.core.database import Base, SessionLocal, get_db  # noqa: E402
from app.core.security import criar_token, hash_senha  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Cliente,
    Container,
    Escala,
    Janela,
    Navio,
    PosicaoPatio,
    Usuario,
)
from app.services.iso6346 import completar  # noqa: E402

SENHA = "senha-de-teste"


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(eng, "connect")
    def _fks(conexao, _):
        conexao.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine) -> Session:
    sessao = SessionLocal(bind=engine)
    yield sessao
    sessao.close()


@pytest.fixture
def client(engine):
    def _db():
        sessao = SessionLocal(bind=engine)
        try:
            yield sessao
        finally:
            sessao.close()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class Fabrica:
    """Cria registros válidos com o mínimo de parâmetros."""

    def __init__(self, db: Session):
        self.db = db
        self._seq = count(1)

    def _salvar(self, obj):
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def cliente(self, razao_social: str | None = None) -> Cliente:
        n = next(self._seq)
        return self._salvar(Cliente(razao_social=razao_social or f"Cliente {n}", cnpj=f"{n:014d}"))

    def usuario(
        self,
        papel: str = Papel.EXTERNO,
        cliente: Cliente | None = None,
        status: str = StatusUsuario.ATIVO,
        email: str | None = None,
    ) -> Usuario:
        n = next(self._seq)
        if papel == Papel.EXTERNO and cliente is None:
            cliente = self.cliente()
        return self._salvar(
            Usuario(
                nome=f"Usuário {n}",
                email=email or f"usuario{n}@teste.com",
                senha_hash=hash_senha(SENHA),
                papel=papel,
                status=status,
                cliente_id=cliente.id if cliente else None,
            )
        )

    def headers(self, usuario: Usuario) -> dict:
        return {"Authorization": f"Bearer {criar_token(usuario.id, usuario.papel)}"}

    def escala(self) -> Escala:
        n = next(self._seq)
        navio = self._salvar(Navio(nome=f"Navio {n}", imo=f"{9000000 + n}", armador="Armador"))
        agora = datetime.now(timezone.utc)
        return self._salvar(
            Escala(navio_id=navio.id, viagem=f"V{n:03d}", eta=agora, etd=agora + timedelta(days=1))
        )

    def posicoes(self, pilhas: int = 2, alturas: int = 3, bloco: str = "A") -> list[PosicaoPatio]:
        lista = [
            PosicaoPatio(bloco=bloco, fileira=1, pilha=p, altura=a)
            for p in range(1, pilhas + 1)
            for a in range(1, alturas + 1)
        ]
        self.db.add_all(lista)
        self.db.commit()
        return lista

    def codigo(self) -> str:
        return completar(f"TSTU{next(self._seq):06d}")

    def container(
        self,
        cliente: Cliente | None = None,
        escala: Escala | None = None,
        status: str = StatusContainer.AGUARDANDO,
        posicao: PosicaoPatio | None = None,
        tamanho: int = 20,
        bloqueado: bool = False,
    ) -> Container:
        return self._salvar(
            Container(
                codigo=self.codigo(),
                tamanho=tamanho,
                tipo="dry",
                peso_kg=Decimal("10000.00"),
                cheio=True,
                status=status,
                bloqueado=bloqueado,
                posicao_id=posicao.id if posicao else None,
                cliente_id=(cliente or self.cliente()).id,
                escala_id=(escala or self.escala()).id,
            )
        )

    def janela(
        self,
        inicio: datetime | None = None,
        duracao_h: int = 1,
        vagas: int = 5,
        livres: int | None = None,
    ) -> Janela:
        inicio = inicio or datetime.now(timezone.utc) - timedelta(minutes=30)
        return self._salvar(
            Janela(
                inicio=inicio,
                fim=inicio + timedelta(hours=duracao_h),
                vagas_total=vagas,
                vagas_livres=vagas if livres is None else livres,
            )
        )


@pytest.fixture
def fab(db) -> Fabrica:
    return Fabrica(db)


@pytest.fixture
def admin(fab):
    return fab.usuario(Papel.ADMIN)


@pytest.fixture
def operador(fab):
    return fab.usuario(Papel.OPERADOR)


@pytest.fixture
def externo(fab):
    return fab.usuario(Papel.EXTERNO)
