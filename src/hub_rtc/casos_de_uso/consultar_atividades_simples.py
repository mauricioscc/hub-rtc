from datetime import date

from hub_rtc.dominio.catalogo import AtividadeSimples
from hub_rtc.portas.calculadora_simples_nacional import CatalogoAtividades


class ConsultarAtividadesSimples:
    def __init__(self, catalogo: CatalogoAtividades) -> None:
        self._catalogo = catalogo

    def executar(self, data: date) -> tuple[AtividadeSimples, ...]:
        return self._catalogo.atividades(data)
