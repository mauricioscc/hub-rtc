from datetime import UTC, datetime
from decimal import Decimal

import pytest

from hub_rtc.dominio.erros import OperacaoInvalida
from hub_rtc.dominio.operacao import (
    AliquotasNominais,
    AliquotasSeletivo,
    ImpostoSeletivoItem,
    ItemOperacao,
    Operacao,
)


def um_item(**alteracoes: object) -> ItemOperacao:
    dados: dict[str, object] = {
        "numero": 1,
        "cst": "000",
        "classificacao_tributaria": "000001",
        "base_calculo": Decimal("25.00"),
    }
    return ItemOperacao(**{**dados, **alteracoes})  # type: ignore[arg-type]


def uma_operacao(itens: tuple[ItemOperacao, ...]) -> Operacao:
    return Operacao(
        fato_gerador=datetime(2026, 10, 20, 10, 0, tzinfo=UTC),
        municipio=3550308,
        uf="SP",
        itens=itens,
    )


def test_item_valido_e_aceito() -> None:
    assert um_item().cst == "000"


@pytest.mark.parametrize("cst", ["00", "0000", "abc", ""])
def test_cst_precisa_ter_tres_digitos(cst: str) -> None:
    with pytest.raises(OperacaoInvalida, match="CST"):
        um_item(cst=cst)


@pytest.mark.parametrize("classificacao", ["00001", "0000001", "abcdef"])
def test_classificacao_precisa_ter_seis_digitos(classificacao: str) -> None:
    with pytest.raises(OperacaoInvalida, match="classificação"):
        um_item(classificacao_tributaria=classificacao)


def test_base_de_calculo_nao_pode_ser_negativa() -> None:
    with pytest.raises(OperacaoInvalida, match="base de cálculo"):
        um_item(base_calculo=Decimal("-0.01"))


def test_numero_do_item_precisa_ser_positivo() -> None:
    with pytest.raises(OperacaoInvalida, match="número do item"):
        um_item(numero=0)


def test_operacao_precisa_de_ao_menos_um_item() -> None:
    with pytest.raises(OperacaoInvalida, match="ao menos um item"):
        uma_operacao(())


def test_numeros_de_item_nao_podem_repetir() -> None:
    with pytest.raises(OperacaoInvalida, match="repetido"):
        uma_operacao((um_item(numero=1), um_item(numero=1)))


def test_uf_precisa_ter_duas_letras() -> None:
    with pytest.raises(OperacaoInvalida, match="UF"):
        Operacao(
            fato_gerador=datetime(2026, 10, 20, tzinfo=UTC),
            municipio=3550308,
            uf="SAO",
            itens=(um_item(),),
        )


def test_aliquotas_nominais_validas_sao_aceitas() -> None:
    aliquotas = AliquotasNominais(
        cbs=Decimal("8.8"), ibs_estadual=Decimal("8.85"), ibs_municipal=Decimal("8.85")
    )

    assert aliquotas.cbs == Decimal("8.8")


@pytest.mark.parametrize("invalida", [Decimal("-0.1"), Decimal("100.01")])
def test_aliquota_nominal_precisa_estar_entre_zero_e_cem(invalida: Decimal) -> None:
    with pytest.raises(OperacaoInvalida, match="alíquota nominal"):
        AliquotasNominais(cbs=invalida, ibs_estadual=Decimal(1), ibs_municipal=Decimal(1))


def test_operacao_guarda_as_aliquotas_nominais() -> None:
    aliquotas = AliquotasNominais(Decimal("8.8"), Decimal("8.85"), Decimal("8.85"))
    operacao = Operacao(
        fato_gerador=datetime(2027, 1, 5, tzinfo=UTC),
        municipio=3304557,
        uf="RJ",
        itens=(um_item(),),
        aliquotas_nominais=aliquotas,
    )

    assert operacao.aliquotas_nominais is aliquotas
    assert uma_operacao((um_item(),)).aliquotas_nominais is None


def um_seletivo(**alteracoes: object) -> ImpostoSeletivoItem:
    dados: dict[str, object] = {
        "cst": "000",
        "classificacao_tributaria": "000001",
        "base_calculo": Decimal("188.00"),
        "quantidade": Decimal(1),
        "unidade": "UN",
    }
    return ImpostoSeletivoItem(**{**dados, **alteracoes})  # type: ignore[arg-type]


def test_item_com_imposto_seletivo_pode_omitir_a_base_de_cbs_e_ibs() -> None:
    item = um_item(base_calculo=None, imposto_seletivo=um_seletivo())

    assert item.base_calculo is None


def test_item_sem_imposto_seletivo_exige_base_de_calculo() -> None:
    with pytest.raises(OperacaoInvalida, match="base de cálculo"):
        um_item(base_calculo=None)


@pytest.mark.parametrize(
    ("alteracao", "trecho"),
    [
        ({"cst": "00"}, "CST do Imposto Seletivo"),
        ({"classificacao_tributaria": "1"}, "classificação do Imposto Seletivo"),
        ({"base_calculo": Decimal(-1)}, "base de cálculo do Imposto Seletivo"),
        ({"quantidade": Decimal(-1)}, "quantidade"),
    ],
)
def test_imposto_seletivo_do_item_e_validado(alteracao: dict[str, object], trecho: str) -> None:
    with pytest.raises(OperacaoInvalida, match=trecho):
        um_seletivo(**alteracao)


def test_aliquotas_do_imposto_seletivo_sao_validadas() -> None:
    assert AliquotasSeletivo(Decimal(10), Decimal("0.5")).ad_rem == Decimal("0.5")
    with pytest.raises(OperacaoInvalida, match="ad valorem"):
        AliquotasSeletivo(Decimal("100.1"), Decimal(0))
    with pytest.raises(OperacaoInvalida, match="ad rem"):
        AliquotasSeletivo(Decimal(0), Decimal(-1))


def test_aliquotas_nominais_podem_trazer_as_do_imposto_seletivo() -> None:
    seletivo = AliquotasSeletivo(Decimal(10), Decimal("0.5"))

    aliquotas = AliquotasNominais(Decimal(1), Decimal(1), Decimal(1), imposto_seletivo=seletivo)

    assert aliquotas.imposto_seletivo is seletivo
