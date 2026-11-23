from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import registrar_handlers
from app.routers import agenda, auth, containers, escalas, usuarios

DESCRICAO = """
API do **PortoFlow**: gestão de containers em terminal portuário.

Perfis: `admin`, `operador` e `externo`. Para testar rotas protegidas, faça
`POST /auth/login`, copie o `access_token` e use o botão **Authorize**.
"""


def criar_app() -> FastAPI:
    app = FastAPI(title="PortoFlow API", version="1.0.0", description=DESCRICAO)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in get_settings().cors_origem.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_handlers(app)

    for modulo in (auth, usuarios, escalas, containers, agenda):
        app.include_router(modulo.router)

    @app.get("/saude", tags=["Infra"], summary="Verificação de saúde")
    def saude():
        return {"status": "ok"}

    return app


app = criar_app()
