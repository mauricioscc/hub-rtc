from datetime import date
from decimal import Decimal

import pytest

from hub_rtc.dominio.erros import OperacaoInvalida
from hub_rtc.dominio.simples_nacional import (
    AliquotasEfetivas,
    AnexoAliquotas,
    ItemSimples,
    OperacaoSimples,
    ParAliquotas,
)


def um_par() -> ParAliquotas:
    return ParAliquotas(cbs=Decimal("1.1612"), ibs=Decimal("0.0129"))


def umas_aliquotas(**alteracoes: object) -> AliquotasEfetivas:
    dados: dict[str, object] = {"anexos": {"I": AnexoAliquotas(um_par())}}
    return AliquotasEfetivas(**{**dados, **alteracoes})  # type: ignore[arg-type]


def um_item(**alteracoes: object) -> ItemSimples:
    dados: dict[str, object] = {
        "numero": 1,
        "atividade": "01",
        "classificacao_tributaria": "000001",
        "base_calculo": Decimal("1000.00"),
    }
    return ItemSimples(**{**dados, **alteracoes})  # type: ignore[arg-type]


def uma_operacao(**alteracoes: object) -> OperacaoSimples:
    dados: dict[str, object] = {
        "data": date(2027, 3, 15),
        "tipo_documento": 55,
        "crt": 1,
        "aliquotas_efetivas": umas_aliquotas(),
        "itens": (um_item(),),
    }
    return OperacaoSimples(**{**dados, **alteracoes})  # type: ignore[arg-type]


def test_operacao_valida_e_aceita() -> None:
    assert uma_operacao().crt == 1


@pytest.mark.parametrize("invalida", [Decimal("-0.1"), Decimal("100.1")])
def test_aliquota_do_par_precisa_estar_entre_zero_e_cem(invalida: Decimal) -> None:
    with pytest.raises(OperacaoInvalida, match="alíquota efetiva"):
        ParAliquotas(cbs=invalida, ibs=Decimal(0))


def test_ibs_do_par_pode_ser_nulo_no_impedimento_pelo_sublimite() -> None:
    assert ParAliquotas(cbs=Decimal(1), ibs=None).ibs is None


def test_anexo_desconhecido_e_recusado() -> None:
    with pytest.raises(OperacaoInvalida, match="anexo"):
        umas_aliquotas(anexos={"VI": AnexoAliquotas(um_par())})


@pytest.mark.parametrize("crt", [0, 3, 4])
def test_crt_so_pode_ser_1_ou_2(crt: int) -> None:
    with pytest.raises(OperacaoInvalida, match="CRT"):
        uma_operacao(crt=crt)


def test_operacao_precisa_de_ao_menos_um_item() -> None:
    with pytest.raises(OperacaoInvalida, match="ao menos um item"):
        uma_operacao(itens=())


def test_numeros_de_item_nao_podem_repetir() -> None:
    with pytest.raises(OperacaoInvalida, match="repetido"):
        uma_operacao(itens=(um_item(numero=1), um_item(numero=1)))


@pytest.mark.parametrize("atividade", ["1", "001", "ab"])
def test_atividade_precisa_ter_dois_digitos(atividade: str) -> None:
    with pytest.raises(OperacaoInvalida, match="atividade"):
        um_item(atividade=atividade)


def test_classificacao_precisa_ter_seis_digitos() -> None:
    with pytest.raises(OperacaoInvalida, match="classificação"):
        um_item(classificacao_tributaria="1")


@pytest.mark.parametrize("campo", ["base_calculo", "valor_imposto_seletivo"])
def test_valores_do_item_nao_podem_ser_negativos(campo: str) -> None:
    with pytest.raises(OperacaoInvalida, match="negativ"):
        um_item(**{campo: Decimal("-1")})


def test_numero_do_item_precisa_ser_positivo() -> None:
    with pytest.raises(OperacaoInvalida, match="número do item"):
        um_item(numero=0)


def test_nbs_do_item_precisa_ter_nove_digitos() -> None:
    assert um_item(nbs="114051000").nbs == "114051000"
    with pytest.raises(OperacaoInvalida, match="NBS"):
        um_item(nbs="123")
