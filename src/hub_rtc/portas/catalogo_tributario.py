from datetime import date
from typing import Protocol

from hub_rtc.dominio.catalogo import SituacaoTributaria


class CatalogoTributario(Protocol):
    """Quem conhece as situações e classificações tributárias vigentes numa data."""

    def situacoes_tributarias(self, data: date) -> tuple[SituacaoTributaria, ...]: ...
