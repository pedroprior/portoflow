"""Regras físicas do pátio (UC05).

- Uma posição comporta um container.
- Acima da altura 1, só se empilha sobre outro container (não há container "flutuando").
- Só se move ou retira um container que não tenha outro em cima.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import StatusContainer, TipoMovimentacao
from app.core.errors import conflito, nao_encontrado
from app.models import Container, Movimentacao, PosicaoPatio, Usuario
from app.repositories import containers as repo
from app.repositories.base import obter_ou_404


def listar_posicoes(db: Session, somente_livres: bool = False) -> list[dict]:
    posicoes = db.scalars(
        select(PosicaoPatio).order_by(
            PosicaoPatio.bloco, PosicaoPatio.fileira, PosicaoPatio.pilha, PosicaoPatio.altura
        )
    ).all()
    ocupantes = {
        c.posicao_id: c
        for c in db.scalars(select(Container).where(Container.posicao_id.is_not(None)))
    }
    ocupadas = set(ocupantes)
    saida = []
    for p in posicoes:
        ocupada = p.id in ocupadas
        if somente_livres and (ocupada or not _tem_apoio(p, ocupadas, posicoes)):
            continue
        c = ocupantes.get(p.id)
        saida.append(
            {
                "id": p.id,
                "bloco": p.bloco,
                "fileira": p.fileira,
                "pilha": p.pilha,
                "altura": p.altura,
                "endereco": p.endereco,
                "ocupada": ocupada,
                "container": (
                    {"id": c.id, "codigo": c.codigo, "bloqueado": c.bloqueado, "tamanho": c.tamanho}
                    if c
                    else None
                ),
            }
        )
    return saida


def _tem_apoio(posicao: PosicaoPatio, ocupadas: set[int], todas) -> bool:
    if posicao.altura == 1:
        return True
    for p in todas:
        if (p.bloco, p.fileira, p.pilha, p.altura) == (
            posicao.bloco,
            posicao.fileira,
            posicao.pilha,
            posicao.altura - 1,
        ):
            return p.id in ocupadas
    return False


def tem_container_acima(db: Session, posicao: PosicaoPatio) -> bool:
    acima = repo.posicao_vizinha(db, posicao, +1)
    return acima is not None and repo.ocupante(db, acima.id) is not None


def validar_destino(db: Session, destino: PosicaoPatio, container_id: int | None = None) -> None:
    if repo.ocupante(db, destino.id) is not None:
        raise conflito("posicao_ocupada", f"A posição {destino.endereco} já está ocupada")
    if destino.altura > 1:
        abaixo = repo.posicao_vizinha(db, destino, -1)
        apoio = repo.ocupante(db, abaixo.id) if abaixo else None
        if apoio is None or apoio.id == container_id:
            raise conflito("sem_apoio", f"Não há container embaixo da posição {destino.endereco}")


def sugerir_posicao(db: Session) -> PosicaoPatio | None:
    """Posição livre e com apoio, ocupando primeiro o chão, depois o 2º nível e assim por diante.

    Empilhar só quando falta chão reduz remoções: cada container posto em cima de
    outro obriga a mover esse de cima quando o de baixo precisar sair.
    """
    livres = listar_posicoes(db, somente_livres=True)
    if not livres:
        return None
    melhor = min(livres, key=lambda p: (p["altura"], p["bloco"], p["fileira"], p["pilha"]))
    return db.get(PosicaoPatio, melhor["id"])


def movimentar(db: Session, operador: Usuario, container_id: int, posicao_id: int) -> Container:
    container = obter_ou_404(db, Container, container_id, "Container")
    if container.status != StatusContainer.NO_PATIO or container.posicao is None:
        raise conflito("fora_do_patio", "Só é possível movimentar container que está no pátio")
    destino = db.get(PosicaoPatio, posicao_id)
    if destino is None:
        raise nao_encontrado("Posição não encontrada")
    origem = container.posicao
    if destino.id == origem.id:
        raise conflito("mesma_posicao", "O container já está nesta posição")
    if tem_container_acima(db, origem):
        raise conflito("container_por_baixo", "Há outro container em cima deste")
    validar_destino(db, destino, container.id)

    container.posicao_id = destino.id
    db.add(
        Movimentacao(
            container_id=container.id,
            tipo=TipoMovimentacao.REMOCAO,
            origem_id=origem.id,
            destino_id=destino.id,
            usuario_id=operador.id,
        )
    )
    db.commit()
    db.refresh(container)
    return container
