from datetime import date

from hub_rtc.casos_de_uso.consultar_situacoes_tributarias import ConsultarSituacoesTributarias
from hub_rtc.dominio.catalogo import SituacaoTributaria

SITUACAO = SituacaoTributaria(codigo="000", descricao="Tributação integral", classificacoes=())


class CatalogoFalso:
    def __init__(self) -> None:
        self.data_pedida: date | None = None

    def situacoes_tributarias(self, data: date) -> tuple[SituacaoTributaria, ...]:
        self.data_pedida = data
        return (SITUACAO,)


def test_repassa_a_data_ao_catalogo_e_devolve_as_situacoes() -> None:
    catalogo = CatalogoFalso()

    situacoes = ConsultarSituacoesTributarias(catalogo).executar(date(2026, 10, 20))

    assert catalogo.data_pedida == date(2026, 10, 20)
    assert situacoes == (SITUACAO,)
