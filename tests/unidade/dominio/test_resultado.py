from decimal import Decimal

from hub_rtc.dominio.resultado import ResultadoCalculo, TributosDoItem


def tributos(cbs: str, ibs_cada: str, seletivo: str) -> TributosDoItem:
    return TributosDoItem(
        numero=1,
        base_calculo_ibs_cbs=Decimal("100.00"),
        cbs=Decimal(cbs),
        ibs_uf=Decimal(ibs_cada),
        ibs_municipal=Decimal(ibs_cada),
        imposto_seletivo=Decimal(seletivo),
    )


def test_ibs_do_item_soma_estado_e_municipio() -> None:
    assert tributos("8.40", "0.10", "0").ibs == Decimal("0.20")


def test_totais_somam_os_itens() -> None:
    resultado = ResultadoCalculo(
        itens=(
            tributos("16.80", "0.10", "47.30"),
            tributos("20.77", "0.12", "0"),
        )
    )

    assert resultado.total_cbs == Decimal("37.57")
    assert resultado.total_ibs == Decimal("0.44")
    assert resultado.total_imposto_seletivo == Decimal("47.30")


def test_resultado_sem_itens_tem_totais_zerados() -> None:
    assert ResultadoCalculo(itens=()).total_cbs == Decimal(0)
