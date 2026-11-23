from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (ou de um arquivo .env).

    Nenhum segredo tem valor padrão: sem DATABASE_URL e JWT_SECRET a API não sobe.
    """

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_algoritmo: str = "HS256"
    jwt_expira_min: int = 60
    cors_origem: str = "http://localhost:5173"
    bcrypt_rounds: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
