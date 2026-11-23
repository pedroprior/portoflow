"""Tratamento de erros centralizado: toda resposta de erro tem o formato
{"erro": {"codigo": "...", "mensagem": "...", "detalhes": [...]?}}."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErroAPI(Exception):
    def __init__(self, status: int, codigo: str, mensagem: str, detalhes: list | None = None):
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes


def nao_autenticado(mensagem: str = "Autenticação necessária") -> ErroAPI:
    return ErroAPI(401, "nao_autenticado", mensagem)


def proibido(mensagem: str = "Você não tem permissão para esta ação") -> ErroAPI:
    return ErroAPI(403, "proibido", mensagem)


def nao_encontrado(mensagem: str) -> ErroAPI:
    return ErroAPI(404, "nao_encontrado", mensagem)


def conflito(codigo: str, mensagem: str) -> ErroAPI:
    return ErroAPI(409, codigo, mensagem)


def invalido(codigo: str, mensagem: str) -> ErroAPI:
    return ErroAPI(422, codigo, mensagem)


def requisicao_ruim(codigo: str, mensagem: str) -> ErroAPI:
    return ErroAPI(400, codigo, mensagem)


def _corpo(codigo: str, mensagem: str, detalhes: list | None = None) -> dict:
    erro: dict = {"codigo": codigo, "mensagem": mensagem}
    if detalhes:
        erro["detalhes"] = detalhes
    return {"erro": erro}


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroAPI)
    async def _erro_api(_: Request, exc: ErroAPI):
        return JSONResponse(status_code=exc.status, content=_corpo(exc.codigo, exc.mensagem, exc.detalhes))

    @app.exception_handler(StarletteHTTPException)
    async def _erro_http(_: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=_corpo(f"http_{exc.status_code}", str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def _erro_validacao(_: Request, exc: RequestValidationError):
        detalhes = [
            {"campo": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]), "mensagem": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content=_corpo("validacao", "Dados inválidos", detalhes))

    @app.exception_handler(IntegrityError)
    async def _erro_integridade(_: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=409, content=_corpo("integridade", "A operação viola uma restrição do banco de dados")
        )
