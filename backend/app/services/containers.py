"""Regras de containers (UC02, UC06, UC07)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import Operacao, Papel, StatusAgendamento, StatusContainer
from app.core.errors import conflito, invalido, nao_encontrado
from app.core.tempo import agora_utc
from app.models import Bloqueio, Cliente, Container, Escala, Janela, Usuario
from app.repositories import containers as repo
from app.repositories.base import obter_ou_404, paginar
from app.schemas.containers import ContainerAtualizar, ContainerEntrada
from app.services import iso6346


def listar(
    db: Session,
    usuario: Usuario,
    busca: str | None,
    status: str | None,
    escala_id: int | None,
    cliente_id: int | None,
    pagina: int,
    tamanho: int,
) -> dict:
    if usuario.papel == Papel.EXTERNO:
        cliente_id = usuario.cliente_id  # usuário externo só vê os containers do seu cliente
    consulta = repo.consulta_listagem(busca, status, escala_id, cliente_id)
    return paginar(db, consulta, pagina, tamanho)


def obter(db: Session, usuario: Usuario, container_id: int) -> Container:
    container = db.get(Container, container_id)
    if (
        container is None
        or not container.ativo
        or (usuario.papel == Papel.EXTERNO and container.cliente_id != usuario.cliente_id)
    ):
        # Para o externo, container de outro cliente responde 404: não revela que existe.
        raise nao_encontrado("Container não encontrado")
    return container


def _validar_escala(db: Session, escala_id: int) -> Escala:
    escala = db.get(Escala, escala_id)
    if escala is None or not escala.ativo:
        raise invalido("escala_invalida", "Escala não encontrada ou inativa")
    return escala


def criar(db: Session, dados: ContainerEntrada) -> Container:
    codigo = iso6346.normalizar(dados.codigo)
    if not iso6346.codigo_valido(codigo):
        raise invalido(
            "codigo_invalido",
            "Código fora do padrão ISO 6346 ou dígito verificador não confere",
        )
    if repo.por_codigo(db, codigo):
        raise conflito("container_duplicado", "Já existe um container ativo com este código")
    cliente = db.get(Cliente, dados.cliente_id)
    if cliente is None or not cliente.ativo:
        raise invalido("cliente_invalido", "Cliente não encontrado ou inativo")
    _validar_escala(db, dados.escala_id)

    container = Container(
        **dados.model_dump(exclude={"codigo"}),
        codigo=codigo,
        status=StatusContainer.AGUARDANDO,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


def atualizar(db: Session, container_id: int, dados: ContainerAtualizar) -> Container:
    container = obter_ou_404(db, Container, container_id, "Container")
    campos = dados.model_dump(exclude_unset=True)
    if "escala_id" in campos:
        _validar_escala(db, campos["escala_id"])
    for campo, valor in campos.items():
        setattr(container, campo, valor)
    db.commit()
    db.refresh(container)
    return container


def desativar(db: Session, container_id: int) -> None:
    container = obter_ou_404(db, Container, container_id, "Container")
    if container.status == StatusContainer.NO_PATIO:
        raise conflito("container_no_patio", "Container no pátio não pode ser desativado")
    if repo.agendamentos_ativos(db, container.id):
        raise conflito("agendamento_ativo", "Container tem agendamento confirmado")
    container.ativo = False  # soft delete: preserva movimentações e agendamentos
    db.commit()


# --- bloqueio e liberação (UC06) ------------------------------------------


def bloquear(db: Session, admin: Usuario, container_id: int, motivo: str) -> Bloqueio:
    container = obter_ou_404(db, Container, container_id, "Container")
    if container.bloqueado:
        raise conflito("ja_bloqueado", "Container já está bloqueado")

    container.bloqueado = True
    bloqueio = Bloqueio(container_id=container.id, motivo=motivo.strip(), criado_por=admin.id)
    db.add(bloqueio)

    # Retiradas agendadas deixam de valer e devolvem a vaga da janela.
    for agendamento in repo.agendamentos_ativos(db, container.id, Operacao.RETIRADA):
        agendamento.status = StatusAgendamento.CANCELADO
        janela = db.scalar(select(Janela).where(Janela.id == agendamento.janela_id).with_for_update())
        janela.vagas_livres += 1

    db.commit()
    db.refresh(bloqueio)
    return bloqueio


def liberar(db: Session, admin: Usuario, container_id: int, bloqueio_id: int) -> None:
    container = obter_ou_404(db, Container, container_id, "Container")
    bloqueio = db.get(Bloqueio, bloqueio_id)
    if bloqueio is None or bloqueio.container_id != container.id:
        raise nao_encontrado("Bloqueio não encontrado")
    if bloqueio.liberado_em is not None:
        raise conflito("ja_liberado", "Este bloqueio já foi liberado")
    bloqueio.liberado_por = admin.id
    bloqueio.liberado_em = agora_utc()
    container.bloqueado = False
    db.commit()


def motivo_bloqueio_atual(container: Container) -> str:
    abertos = [b for b in container.bloqueios if b.liberado_em is None]
    return abertos[-1].motivo if abertos else "sem motivo registrado"
