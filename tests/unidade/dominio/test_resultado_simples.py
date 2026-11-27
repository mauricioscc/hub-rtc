from decimal import Decimal

from hub_rtc.dominio.resultado_simples import ItemSimplesCalculado, ResultadoSimples


def test_total_do_item_soma_cbs_ibs_e_imposto_seletivo() -> None:
    item = ItemSimplesCalculado(
        numero=1,
        situacao="CALCULADO",
        cbs=Decimal("11.61"),
        ibs=Decimal("0.13"),
        imposto_seletivo=Decimal("5.00"),
    )

    assert item.total == Decimal("16.74")


def test_totais_somam_os_itens_e_item_nao_calculado_vale_zero() -> None:
    calculado = ItemSimplesCalculado(
        numero=1, situacao="CALCULADO", cbs=Decimal("11.61"), ibs=Decimal("0.13")
    )
    recusado = ItemSimplesCalculado(
        numero=2, situacao="NAO_CALCULADO", mensagens=("atividade desconhecida",)
    )

    resultado = ResultadoSimples(itens=(calculado, recusado))

    assert resultado.total_cbs == Decimal("11.61")
    assert resultado.total_ibs == Decimal("0.13")
    assert resultado.total_imposto_seletivo == Decimal(0)
    assert resultado.total_tributos == Decimal("11.74")
