from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.constantes import TRANSICOES_AGENDAMENTO, TRANSICOES_ESCALA
from app.core.errors import ErroAPI
from app.core.tempo import como_utc
from app.schemas.agenda import AgendamentoEntrada, JanelaEntrada
from app.schemas.comum import normalizar_placa
from app.schemas.containers import ContainerEntrada
from app.schemas.escalas import EscalaEntrada
from app.schemas.usuarios import PerfilAtualizar, RegistroEntrada, UsuarioCriar
from app.services.transicoes import validar_transicao

# --- transições de status --------------------------------------------------


@pytest.mark.parametrize("novo", ["cumprido", "cancelado", "confirmado"])
def test_agendamento_confirmado_pode_avancar_ou_ficar(novo):
    validar_transicao("confirmado", novo, TRANSICOES_AGENDAMENTO, "Agendamento")


@pytest.mark.parametrize("atual, novo", [("cancelado", "confirmado"), ("cumprido", "cancelado")])
def test_agendamento_finalizado_nao_muda(atual, novo):
    with pytest.raises(ErroAPI) as erro:
        validar_transicao(atual, novo, TRANSICOES_AGENDAMENTO, "Agendamento")
    assert erro.value.status == 409
    assert erro.value.codigo == "transicao_invalida"


def test_escala_nao_pula_etapa():
    with pytest.raises(ErroAPI):
        validar_transicao("prevista", "encerrada", TRANSICOES_ESCALA, "Escala")
    validar_transicao("prevista", "atracada", TRANSICOES_ESCALA, "Escala")


# --- tempo -----------------------------------------------------------------


def test_como_utc_trata_datetime_sem_fuso_como_utc():
    ingenuo = datetime(2026, 1, 1, 12, 0)
    assert como_utc(ingenuo) == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_como_utc_converte_outro_fuso():
    brasilia = datetime(2026, 1, 1, 9, 0, tzinfo=timezone(timedelta(hours=-3)))
    assert como_utc(brasilia).hour == 12


# --- placa -----------------------------------------------------------------


@pytest.mark.parametrize(
    "entrada, esperado", [("abc-1234", "ABC1234"), ("ABC1D23", "ABC1D23"), (" abc 1d23 ", "ABC1D23")]
)
def test_placa_normalizada(entrada, esperado):
    assert normalizar_placa(entrada) == esperado


@pytest.mark.parametrize("placa", ["AB1234", "ABCD123", "1BC1234", "ABC12345"])
def test_placa_invalida(placa):
    with pytest.raises(ValueError):
        normalizar_placa(placa)


# --- esquemas de entrada ---------------------------------------------------

AGENDAMENTO = {"janela_id": 1, "operacao": "entrega", "placa": "abc1d23", "motorista": "João"}


def test_agendamento_aceita_ate_dois_containers():
    dados = AgendamentoEntrada(**AGENDAMENTO, container_ids=[1, 2])
    assert dados.placa == "ABC1D23"


@pytest.mark.parametrize("ids", [[], [1, 2, 3], [5, 5]])
def test_agendamento_rejeita_lista_de_containers_invalida(ids):
    with pytest.raises(ValidationError):
        AgendamentoEntrada(**AGENDAMENTO, container_ids=ids)


def test_escala_exige_saida_depois_da_atracacao():
    eta = datetime(2026, 12, 1, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        EscalaEntrada(navio_id=1, viagem="1", eta=eta, etd=eta - timedelta(hours=1))


def test_janela_exige_fim_depois_do_inicio():
    inicio = datetime(2026, 12, 1, 8, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        JanelaEntrada(inicio=inicio, fim=inicio, vagas_total=5)


CONTAINER = {
    "codigo": "CSQU3054383",
    "tamanho": 20,
    "tipo": "dry",
    "cheio": True,
    "cliente_id": 1,
    "escala_id": 1,
}


@pytest.mark.parametrize("peso", ["0", "-10", "12.345", "123456789.00"])
def test_container_rejeita_peso_invalido(peso):
    with pytest.raises(ValidationError):
        ContainerEntrada(**CONTAINER, peso_kg=peso)


def test_container_peso_e_decimal_exato():
    dados = ContainerEntrada(**CONTAINER, peso_kg="0.10")
    assert dados.peso_kg == Decimal("0.10")
    assert dados.peso_kg * 3 == Decimal("0.30")  # com float daria 0.30000000000000004


def test_container_tamanho_so_20_ou_40():
    with pytest.raises(ValidationError):
        ContainerEntrada(**{**CONTAINER, "tamanho": 30}, peso_kg="100")


def test_registro_normaliza_cnpj():
    dados = RegistroEntrada(nome="Ana", email="a@b.com", senha="12345678", cnpj="12.345.678/0001-90")
    assert dados.cnpj == "12345678000190"


def test_registro_rejeita_cnpj_curto_e_senha_curta():
    with pytest.raises(ValidationError):
        RegistroEntrada(nome="Ana", email="a@b.com", senha="12345678", cnpj="123")
    with pytest.raises(ValidationError):
        RegistroEntrada(nome="Ana", email="a@b.com", senha="123", cnpj="12345678000190")


def test_usuario_externo_exige_cliente():
    with pytest.raises(ValidationError):
        UsuarioCriar(nome="Ana", email="a@b.com", senha="12345678", papel="externo")
    UsuarioCriar(nome="Op", email="o@b.com", senha="12345678", papel="operador")


def test_trocar_senha_exige_senha_atual():
    with pytest.raises(ValidationError):
        PerfilAtualizar(nova_senha="novaSenha123")
