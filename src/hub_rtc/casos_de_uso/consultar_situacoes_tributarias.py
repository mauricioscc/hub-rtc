from datetime import date

from hub_rtc.dominio.catalogo import SituacaoTributaria
from hub_rtc.portas.catalogo_tributario import CatalogoTributario


class ConsultarSituacoesTributarias:
    def __init__(self, catalogo: CatalogoTributario) -> None:
        self._catalogo = catalogo

    def executar(self, data: date) -> tuple[SituacaoTributaria, ...]:
        return self._catalogo.situacoes_tributarias(data)
