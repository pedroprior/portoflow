from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constantes import StatusUsuario
from app.core.database import get_db
from app.core.deps import equipe_terminal, get_usuario_atual, so_admin
from app.models import Usuario
from app.schemas.usuarios import (
    ClienteAtualizar,
    ClienteEntrada,
    ClienteSaida,
    PerfilAtualizar,
    UsuarioAtualizar,
    UsuarioCriar,
    UsuarioSaida,
)
from app.services import usuarios as servico

router = APIRouter(tags=["Usuários e clientes"])


@router.get("/usuarios/me", response_model=UsuarioSaida, summary="Meu perfil")
def meu_perfil(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


@router.put("/usuarios/me", response_model=UsuarioSaida, summary="Editar meu perfil e senha")
def editar_perfil(
    dados: PerfilAtualizar,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    return servico.atualizar_perfil(db, usuario, dados)


@router.get("/usuarios", response_model=list[UsuarioSaida], summary="Listar usuários")
def listar_usuarios(
    status_: StatusUsuario | None = Query(default=None, alias="status"),
    _: Usuario = Depends(so_admin),
    db: Session = Depends(get_db),
):
    return servico.listar(db, status_)


@router.post(
    "/usuarios",
    response_model=UsuarioSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário (qualquer perfil)",
)
def criar_usuario(dados: UsuarioCriar, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    return servico.criar(db, dados)


@router.put(
    "/usuarios/{usuario_id}",
    response_model=UsuarioSaida,
    summary="Editar usuário; status 'ativo' aprova um cadastro pendente",
)
def editar_usuario(
    usuario_id: int,
    dados: UsuarioAtualizar,
    admin: Usuario = Depends(so_admin),
    db: Session = Depends(get_db),
):
    return servico.atualizar(db, admin, usuario_id, dados)


@router.delete(
    "/usuarios/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativar usuário",
)
def desativar_usuario(usuario_id: int, admin: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    servico.desativar(db, admin, usuario_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/clientes", response_model=list[ClienteSaida], summary="Listar clientes")
def listar_clientes(_: Usuario = Depends(equipe_terminal), db: Session = Depends(get_db)):
    return servico.listar_clientes(db)


@router.post(
    "/clientes",
    response_model=ClienteSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar cliente",
)
def criar_cliente(dados: ClienteEntrada, _: Usuario = Depends(so_admin), db: Session = Depends(get_db)):
    return servico.criar_cliente(db, dados)


@router.put("/clientes/{cliente_id}", response_model=ClienteSaida, summary="Editar cliente")
def editar_cliente(
    cliente_id: int,
    dados: ClienteAtualizar,
    _: Usuario = Depends(so_admin),
    db: Session = Depends(get_db),
):
    return servico.atualizar_cliente(db, cliente_id, dados)
