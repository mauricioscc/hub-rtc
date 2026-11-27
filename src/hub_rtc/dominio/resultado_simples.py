"""Tributos do Simples Nacional calculados pelo motor, no vocabulário do Hub."""

from dataclasses import dataclass
from decimal import Decimal

from hub_rtc.dominio.resultado import MemoriaDeCalculo

ITEM_CALCULADO = "CALCULADO"


@dataclass(frozen=True)
class ItemSimplesCalculado:
    numero: int
    # CALCULADO, NAO_CALCULADO ou INCONSISTENCIA_ENTRADA (os dois últimos trazem mensagens).
    situacao: str
    receita_bruta: Decimal = Decimal(0)
    base_calculo: Decimal = Decimal(0)
    aliquota_cbs: Decimal = Decimal(0)
    aliquota_ibs: Decimal = Decimal(0)
    cbs: Decimal = Decimal(0)
    ibs: Decimal = Decimal(0)
    imposto_seletivo: Decimal = Decimal(0)
    anexo: str | None = None
    mensagens: tuple[str, ...] = ()
    memorias_de_calculo: tuple[MemoriaDeCalculo, ...] = ()

    @property
    def total(self) -> Decimal:
        return self.cbs + self.ibs + self.imposto_seletivo


@dataclass(frozen=True)
class ResultadoSimples:
    itens: tuple[ItemSimplesCalculado, ...]
    # SN_PLENO, SN_SUBLIMITE... — como o motor classificou o regime de apuração.
    regime_apuracao: str | None = None
    avisos: tuple[str, ...] = ()

    @property
    def total_cbs(self) -> Decimal:
        return sum((item.cbs for item in self.itens), Decimal(0))

    @property
    def total_ibs(self) -> Decimal:
        return sum((item.ibs for item in self.itens), Decimal(0))

    @property
    def total_imposto_seletivo(self) -> Decimal:
        return sum((item.imposto_seletivo for item in self.itens), Decimal(0))

    @property
    def total_tributos(self) -> Decimal:
        return self.total_cbs + self.total_ibs + self.total_imposto_seletivo
