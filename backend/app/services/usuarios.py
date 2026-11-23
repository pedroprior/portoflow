"""Regras de usuários, autenticação e clientes."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import Papel, StatusUsuario
from app.core.errors import (
    ErroAPI,
    conflito,
    invalido,
    nao_autenticado,
    nao_encontrado,
    requisicao_ruim,
)
from app.core.security import criar_token, hash_senha, verificar_senha
from app.models import Cliente, Usuario
from app.repositories.base import obter_ou_404
from app.schemas.usuarios import (
    ClienteAtualizar,
    ClienteEntrada,
    LoginEntrada,
    PerfilAtualizar,
    RegistroEntrada,
    UsuarioAtualizar,
    UsuarioCriar,
)


def _email_livre(db: Session, email: str) -> None:
    if db.scalar(select(Usuario.id).where(Usuario.email == email.lower())):
        raise conflito("email_duplicado", "Já existe um usuário com este e-mail")


def _cliente_ativo(db: Session, cliente_id: int) -> Cliente:
    cliente = db.get(Cliente, cliente_id)
    if cliente is None or not cliente.ativo:
        raise invalido("cliente_invalido", "Cliente não encontrado ou inativo")
    return cliente


# --- autenticação ---------------------------------------------------------


def registrar(db: Session, dados: RegistroEntrada) -> Usuario:
    """Cadastro público: cria usuário externo pendente de aprovação do administrador."""
    _email_livre(db, dados.email)
    cliente = db.scalar(select(Cliente).where(Cliente.cnpj == dados.cnpj, Cliente.ativo.is_(True)))
    if cliente is None:
        raise invalido("cnpj_desconhecido", "CNPJ não cadastrado no terminal")
    usuario = Usuario(
        nome=dados.nome.strip(),
        email=dados.email.lower(),
        senha_hash=hash_senha(dados.senha),
        papel=Papel.EXTERNO,
        status=StatusUsuario.PENDENTE,
        cliente_id=cliente.id,
    )
    db.add(usuario)
    db.commit()
    return usuario


def autenticar(db: Session, dados: LoginEntrada) -> tuple[str, Usuario]:
    usuario = db.scalar(select(Usuario).where(Usuario.email == dados.email.lower()))
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise nao_autenticado("E-mail ou senha incorretos")
    if usuario.status == StatusUsuario.PENDENTE:
        raise ErroAPI(403, "cadastro_pendente", "Cadastro aguardando aprovação do administrador")
    if usuario.status == StatusUsuario.INATIVO:
        raise ErroAPI(403, "usuario_inativo", "Usuário desativado")
    return criar_token(usuario.id, usuario.papel), usuario


# --- gestão de usuários (admin) -------------------------------------------


def listar(db: Session, status: str | None = None) -> list[Usuario]:
    consulta = select(Usuario).order_by(Usuario.nome)
    if status:
        consulta = consulta.where(Usuario.status == status)
    return list(db.scalars(consulta).all())


def criar(db: Session, dados: UsuarioCriar) -> Usuario:
    _email_livre(db, dados.email)
    cliente_id = None
    if dados.papel == Papel.EXTERNO:
        cliente_id = _cliente_ativo(db, dados.cliente_id).id
    usuario = Usuario(
        nome=dados.nome.strip(),
        email=dados.email.lower(),
        senha_hash=hash_senha(dados.senha),
        papel=dados.papel,
        status=StatusUsuario.ATIVO,
        cliente_id=cliente_id,
    )
    db.add(usuario)
    db.commit()
    return usuario


def atualizar(db: Session, admin: Usuario, usuario_id: int, dados: UsuarioAtualizar) -> Usuario:
    usuario = obter_ou_404(db, Usuario, usuario_id, "Usuário")
    campos = dados.model_dump(exclude_unset=True)
    if usuario.id == admin.id and (
        campos.get("status") == StatusUsuario.INATIVO or campos.get("papel") not in (None, Papel.ADMIN)
    ):
        raise requisicao_ruim("auto_rebaixamento", "Você não pode desativar ou rebaixar o próprio usuário")
    if "cliente_id" in campos and campos["cliente_id"] is not None:
        _cliente_ativo(db, campos["cliente_id"])
    for campo, valor in campos.items():
        setattr(usuario, campo, valor)
    if usuario.papel == Papel.EXTERNO and usuario.cliente_id is None:
        raise invalido("cliente_obrigatorio", "Usuário externo precisa de cliente_id")
    if usuario.papel != Papel.EXTERNO:
        usuario.cliente_id = None
    db.commit()
    return usuario


def desativar(db: Session, admin: Usuario, usuario_id: int) -> None:
    usuario = obter_ou_404(db, Usuario, usuario_id, "Usuário")
    if usuario.id == admin.id:
        raise requisicao_ruim("auto_desativacao", "Você não pode desativar o próprio usuário")
    usuario.status = StatusUsuario.INATIVO
    db.commit()


def atualizar_perfil(db: Session, usuario: Usuario, dados: PerfilAtualizar) -> Usuario:
    if dados.nome:
        usuario.nome = dados.nome.strip()
    if dados.nova_senha:
        if not verificar_senha(dados.senha_atual or "", usuario.senha_hash):
            raise requisicao_ruim("senha_incorreta", "Senha atual incorreta")
        usuario.senha_hash = hash_senha(dados.nova_senha)
    db.commit()
    return usuario


# --- clientes -------------------------------------------------------------


def listar_clientes(db: Session) -> list[Cliente]:
    return list(db.scalars(select(Cliente).order_by(Cliente.razao_social)).all())


def criar_cliente(db: Session, dados: ClienteEntrada) -> Cliente:
    if db.scalar(select(Cliente.id).where(Cliente.cnpj == dados.cnpj)):
        raise conflito("cnpj_duplicado", "Já existe um cliente com este CNPJ")
    cliente = Cliente(razao_social=dados.razao_social.strip(), cnpj=dados.cnpj)
    db.add(cliente)
    db.commit()
    return cliente


def atualizar_cliente(db: Session, cliente_id: int, dados: ClienteAtualizar) -> Cliente:
    cliente = db.get(Cliente, cliente_id)  # inclui inativos: o admin pode reativar
    if cliente is None:
        raise nao_encontrado("Cliente não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    db.commit()
    return cliente
