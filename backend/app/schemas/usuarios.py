import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.constantes import Papel, StatusUsuario
from app.schemas.comum import Saida


def _so_digitos(valor: str) -> str:
    cnpj = re.sub(r"\D", "", valor)
    if len(cnpj) != 14:
        raise ValueError("CNPJ deve ter 14 dígitos")
    return cnpj


Cnpj = Annotated[str, AfterValidator(_so_digitos)]


class RegistroEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    cnpj: Cnpj = Field(description="CNPJ do cliente (empresa) já cadastrado no terminal")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome": "Ana Souza",
                    "email": "ana@transportadora.com.br",
                    "senha": "senhaForte123",
                    "cnpj": "12.345.678/0001-90",
                }
            ]
        }
    )


class LoginEntrada(BaseModel):
    email: EmailStr
    senha: str

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "admin@portoflow.com.br", "senha": "sua-senha"}]}
    )


class TokenSaida(BaseModel):
    access_token: str
    token_type: str = "bearer"
    papel: Papel
    nome: str


class UsuarioSaida(Saida):
    id: int
    nome: str
    email: str
    papel: Papel
    status: StatusUsuario
    cliente_id: int | None
    criado_em: datetime | None = None


class UsuarioCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72, description="Senha inicial; o usuário troca no perfil")
    papel: Papel
    cliente_id: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome": "Carlos Lima",
                    "email": "carlos@portoflow.com.br",
                    "senha": "senhaInicial1",
                    "papel": "operador",
                    "cliente_id": None,
                }
            ]
        }
    )

    @model_validator(mode="after")
    def _externo_tem_cliente(self):
        if self.papel == Papel.EXTERNO and self.cliente_id is None:
            raise ValueError("usuário externo precisa de cliente_id")
        return self


class UsuarioAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    papel: Papel | None = None
    status: StatusUsuario | None = None
    cliente_id: int | None = None


class PerfilAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    senha_atual: str | None = None
    nova_senha: str | None = Field(default=None, min_length=8, max_length=72)

    @model_validator(mode="after")
    def _senha_atual_obrigatoria(self):
        if self.nova_senha and not self.senha_atual:
            raise ValueError("informe a senha atual para trocar a senha")
        return self


class ClienteEntrada(BaseModel):
    razao_social: str = Field(min_length=2, max_length=150)
    cnpj: Cnpj

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"razao_social": "Transportes Oeste Ltda", "cnpj": "12.345.678/0001-90"}]
        }
    )


class ClienteAtualizar(BaseModel):
    razao_social: str | None = Field(default=None, min_length=2, max_length=150)
    ativo: bool | None = None


class ClienteSaida(Saida):
    id: int
    razao_social: str
    cnpj: str
    ativo: bool
