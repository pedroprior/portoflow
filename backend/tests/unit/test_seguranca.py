from datetime import timedelta

import jwt

from app.core.config import get_settings
from app.core.security import criar_token, decodificar_token, hash_senha, verificar_senha
from app.core.tempo import agora_utc


def test_hash_de_senha_nao_guarda_texto_puro():
    h = hash_senha("minha-senha")
    assert "minha-senha" not in h
    assert h.startswith("$2b$")  # bcrypt


def test_mesma_senha_gera_hashes_diferentes():
    assert hash_senha("abc12345") != hash_senha("abc12345")  # salt aleatório


def test_verificar_senha():
    h = hash_senha("correta123")
    assert verificar_senha("correta123", h)
    assert not verificar_senha("errada123", h)


def test_verificar_senha_com_hash_corrompido_devolve_false():
    assert not verificar_senha("qualquer", "isto-nao-e-um-hash")


def test_token_carrega_usuario_e_papel():
    payload = decodificar_token(criar_token(42, "admin"))
    assert payload["sub"] == "42"
    assert payload["papel"] == "admin"
    assert "exp" in payload


def test_token_assinado_com_outra_chave_e_rejeitado():
    falso = jwt.encode({"sub": "1", "papel": "admin"}, "outra-chave", algorithm="HS256")
    assert decodificar_token(falso) is None


def test_token_expirado_e_rejeitado():
    cfg = get_settings()
    vencido = jwt.encode(
        {"sub": "1", "papel": "admin", "exp": agora_utc() - timedelta(minutes=1)},
        cfg.jwt_secret,
        algorithm=cfg.jwt_algoritmo,
    )
    assert decodificar_token(vencido) is None


def test_token_malformado_e_rejeitado():
    assert decodificar_token("abc.def.ghi") is None
