from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import Agendamento, Container, PosicaoPatio, agendamento_container
from app.core.constantes import StatusAgendamento


def consulta_listagem(
    busca: str | None,
    status: str | None,
    escala_id: int | None,
    cliente_id: int | None,
) -> Select:
    """Consulta parametrizada (via ORM) da listagem de containers ativos."""
    consulta = (
        select(Container)
        .options(selectinload(Container.posicao))
        .where(Container.ativo.is_(True))
        .order_by(Container.codigo)
    )
    if busca:
        consulta = consulta.where(Container.codigo.ilike(f"%{busca.strip()}%"))
    if status:
        consulta = consulta.where(Container.status == status)
    if escala_id:
        consulta = consulta.where(Container.escala_id == escala_id)
    if cliente_id:
        consulta = consulta.where(Container.cliente_id == cliente_id)
    return consulta


def por_codigo(db: Session, codigo: str) -> Container | None:
    return db.scalar(
        select(Container).where(Container.codigo == codigo, Container.ativo.is_(True))
    )


def ocupante(db: Session, posicao_id: int) -> Container | None:
    return db.scalar(select(Container).where(Container.posicao_id == posicao_id))


def posicao_vizinha(db: Session, posicao: PosicaoPatio, delta_altura: int) -> PosicaoPatio | None:
    return db.scalar(
        select(PosicaoPatio).where(
            PosicaoPatio.bloco == posicao.bloco,
            PosicaoPatio.fileira == posicao.fileira,
            PosicaoPatio.pilha == posicao.pilha,
            PosicaoPatio.altura == posicao.altura + delta_altura,
        )
    )


def agendamentos_ativos(db: Session, container_id: int, operacao: str | None = None) -> list[Agendamento]:
    consulta = (
        select(Agendamento)
        .join(agendamento_container, agendamento_container.c.agendamento_id == Agendamento.id)
        .where(
            agendamento_container.c.container_id == container_id,
            Agendamento.status == StatusAgendamento.CONFIRMADO,
        )
    )
    if operacao:
        consulta = consulta.where(Agendamento.operacao == operacao)
    return list(db.scalars(consulta).all())
