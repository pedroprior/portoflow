import pytest

from app.services import iso6346


@pytest.mark.parametrize("codigo", ["CSQU3054383", "csqu3054383", "CSQU 305438 3", "CSQU-305438-3"])
def test_codigo_valido_aceita_variacoes_de_escrita(codigo):
    assert iso6346.codigo_valido(codigo)


@pytest.mark.parametrize(
    "codigo, motivo",
    [
        ("CSQU3054384", "dígito verificador errado"),
        ("CSQX3054383", "categoria precisa ser U, J ou Z"),
        ("CSQU305438", "faltando dígito"),
        ("CS1U3054383", "proprietário com número"),
        ("", "vazio"),
    ],
)
def test_codigo_invalido(codigo, motivo):
    assert not iso6346.codigo_valido(codigo), motivo


def test_tabela_de_letras_pula_multiplos_de_11():
    valores = iso6346._VALORES
    assert valores["A"] == 10
    assert valores["B"] == 12  # 11 é pulado
    assert valores["K"] == 21
    assert valores["L"] == 23  # 22 é pulado
    assert valores["U"] == 32
    assert valores["V"] == 34  # 33 é pulado
    assert valores["Z"] == 38
    assert all(v % 11 for v in valores.values())


def test_resto_10_vira_digito_0():
    # Procura uma série cujo resto da divisão por 11 seja 10: o dígito deve ser 0.
    for serie in range(1_000_000):
        base = f"ABCU{serie:06d}"
        total = sum(
            (iso6346._VALORES[c] if c.isalpha() else int(c)) * 2**i for i, c in enumerate(base)
        )
        if total % 11 == 10:
            assert iso6346.digito_verificador(base) == 0
            assert iso6346.codigo_valido(base + "0")
            return
    pytest.fail("nenhuma série com resto 10 encontrada")


def test_completar_gera_codigo_valido():
    codigo = iso6346.completar("MSCU123456")
    assert len(codigo) == 11
    assert iso6346.codigo_valido(codigo)


def test_digito_verificador_rejeita_formato_errado():
    with pytest.raises(ValueError):
        iso6346.digito_verificador("ABC123")


def test_normalizar():
    assert iso6346.normalizar(" msku-123456 7 ") == "MSKU1234567"
