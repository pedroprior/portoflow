"""Carga inicial (seed) do PortoFlow. Idempotente: se o admin já existe, não faz nada.

Cria: 1 admin, 1 operador, 2 clientes com 1 usuário externo cada, 3 navios com
3 escalas, 200 posições de pátio, 20 containers (10 no pátio, 1 deles bloqueado)
e janelas de hora em hora para hoje e os próximos 7 dias.

As senhas vêm de variáveis de ambiente (SEED_SENHA_ADMIN e SEED_SENHA_PADRAO).
Uso: python seed.py
"""

import os
import sys
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import (
    Papel,
    StatusContainer,
    StatusEscala,
    StatusUsuario,
    TipoMovimentacao,
)
from app.core.database import SessionLocal, get_engine
from app.core.security import hash_senha
from app.models import (
    Bloqueio,
    Cliente,
    Container,
    Escala,
    Janela,
    Movimentacao,
    Navio,
    PosicaoPatio,
    Usuario,
)
from app.services.iso6346 import completar

FUSO_PORTO = timezone(timedelta(hours=-3))  # horário de Brasília
ADMIN_EMAIL = "admin@portoflow.com.br"


def _senha(variavel: str) -> str:
    valor = os.environ.get(variavel)
    if not valor:
        sys.exit(f"Defina {variavel} no .env antes de rodar o seed.")
    return valor


def popular(db: Session, senha_admin: str, senha_padrao: str, hoje: datetime | None = None) -> bool:
    if db.scalar(select(Usuario.id).where(Usuario.email == ADMIN_EMAIL)):
        return False

    hoje = hoje or datetime.now(FUSO_PORTO)

    # Clientes e usuários
    oeste = Cliente(razao_social="Transportes Oeste Ltda", cnpj="12345678000190")
    sul = Cliente(razao_social="Importadora Sul S.A.", cnpj="98765432000110")
    db.add_all([oeste, sul])
    db.flush()

    hash_admin, hash_padrao = hash_senha(senha_admin), hash_senha(senha_padrao)
    admin = Usuario(nome="Administrador", email=ADMIN_EMAIL, senha_hash=hash_admin, papel=Papel.ADMIN)
    operador = Usuario(
        nome="Operador do Portão", email="operador@portoflow.com.br", senha_hash=hash_padrao, papel=Papel.OPERADOR
    )
    externos = [
        Usuario(
            nome="Ana Souza",
            email="ana@transportesoeste.com.br",
            senha_hash=hash_padrao,
            papel=Papel.EXTERNO,
            cliente_id=oeste.id,
        ),
        Usuario(
            nome="Bruno Costa",
            email="bruno@importadorasul.com.br",
            senha_hash=hash_padrao,
            papel=Papel.EXTERNO,
            cliente_id=sul.id,
        ),
    ]
    for u in [admin, operador, *externos]:
        u.status = StatusUsuario.ATIVO
    db.add_all([admin, operador, *externos])

    # Navios e escalas
    navios = [
        Navio(nome="MSC Aurora", imo="9876543", armador="MSC"),
        Navio(nome="Maersk Itajaí", imo="9765432", armador="Maersk"),
        Navio(nome="CMA CGM Paranaguá", imo="9654321", armador="CMA CGM"),
    ]
    db.add_all(navios)
    db.flush()
    base = hoje.replace(hour=8, minute=0, second=0, microsecond=0)
    escalas = [
        Escala(navio_id=navios[0].id, viagem="024S", eta=base - timedelta(days=1),
               etd=base + timedelta(days=1), ata=base - timedelta(days=1), status=StatusEscala.ATRACADA),
        Escala(navio_id=navios[1].id, viagem="118N", eta=base + timedelta(days=3),
               etd=base + timedelta(days=4), status=StatusEscala.PREVISTA),
        Escala(navio_id=navios[2].id, viagem="0407E", eta=base + timedelta(days=6),
               etd=base + timedelta(days=7), status=StatusEscala.PREVISTA),
    ]
    db.add_all(escalas)

    # Pátio: 2 blocos x 5 fileiras x 4 pilhas x 5 alturas = 200 posições
    posicoes = [
        PosicaoPatio(bloco=b, fileira=f, pilha=p, altura=a)
        for b in ("A", "B")
        for f in range(1, 6)
        for p in range(1, 5)
        for a in range(1, 6)
    ]
    db.add_all(posicoes)
    db.flush()
    chao = [p for p in posicoes if p.altura == 1]

    # 20 containers: os 10 primeiros já estão no pátio
    donos = ["MSCU", "MAEU", "CMAU", "HLXU", "TGHU"]
    containers = []
    for i in range(20):
        no_patio = i < 10
        c = Container(
            codigo=completar(f"{donos[i % 5]}{305438 + i * 7:06d}"),
            tamanho=40 if i % 4 == 3 else 20,
            tipo="reefer" if i % 6 == 5 else "dry",
            peso_kg=Decimal("8000.00") + Decimal(i * 731) + Decimal("0.50"),
            cheio=i % 5 != 4,
            perigoso=i == 7,
            status=StatusContainer.NO_PATIO if no_patio else StatusContainer.AGUARDANDO,
            posicao_id=chao[i].id if no_patio else None,
            cliente_id=oeste.id if i % 2 == 0 else sul.id,
            escala_id=escalas[i % 3].id,
        )
        containers.append(c)
    db.add_all(containers)
    db.flush()

    for c in containers[:10]:
        db.add(Movimentacao(container_id=c.id, tipo=TipoMovimentacao.GATE_IN,
                            destino_id=c.posicao_id, usuario_id=operador.id))

    bloqueado = containers[2]
    bloqueado.bloqueado = True
    db.add(Bloqueio(container_id=bloqueado.id, motivo="Pendência documental: BL não apresentado",
                    criado_por=admin.id))

    # Janelas de 1 h, das 06h às 22h, hoje e nos próximos 7 dias
    for d in range(8):
        dia = (hoje + timedelta(days=d)).date()
        for h in range(6, 22):
            inicio = datetime.combine(dia, time(h), tzinfo=FUSO_PORTO)
            db.add(Janela(inicio=inicio, fim=inicio + timedelta(hours=1), vagas_total=5, vagas_livres=5))

    db.commit()
    return True


def main() -> None:
    db = SessionLocal(bind=get_engine())
    try:
        criado = popular(db, _senha("SEED_SENHA_ADMIN"), _senha("SEED_SENHA_PADRAO"))
        print("Seed aplicado." if criado else "Seed já aplicado anteriormente; nada a fazer.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
