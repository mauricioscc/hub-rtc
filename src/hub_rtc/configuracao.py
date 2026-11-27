"""Configuração do Hub lida das variáveis de ambiente.

Fica fora das camadas: só a composição (e os testes de fumaça) a usam.
"""

from collections.abc import Mapping
from dataclasses import dataclass

HOST_PADRAO = "localhost"
PORTA_PADRAO_REGIME_REGULAR = "8081"
PORTA_PADRAO_SIMPLES_NACIONAL = "8082"
PORTA_PADRAO_GERADOR_DANFSE = "8083"
PORTA_PADRAO_HUB = "8000"


@dataclass(frozen=True)
class EnderecosMotores:
    """URLs base dos três motores oficiais da Receita Federal."""

    regime_regular: str
    simples_nacional: str
    gerador_danfse: str
    hub: str

    @classmethod
    def do_ambiente(cls, ambiente: Mapping[str, str]) -> "EnderecosMotores":
        host = ambiente.get("HUB_RTC_HOST", HOST_PADRAO)

        def url(motor: str, porta_padrao: str) -> str:
            # URL_<MOTOR> (completa) vence HOST + PORTA_<MOTOR>: serve a rede interna do Docker.
            if completa := ambiente.get(f"URL_{motor}"):
                return completa
            return f"http://{host}:{ambiente.get(f'PORTA_{motor}', porta_padrao)}"

        return cls(
            regime_regular=url("REGIME_REGULAR", PORTA_PADRAO_REGIME_REGULAR),
            simples_nacional=url("SIMPLES_NACIONAL", PORTA_PADRAO_SIMPLES_NACIONAL),
            gerador_danfse=url("GERADOR_DANFSE", PORTA_PADRAO_GERADOR_DANFSE),
            hub=url("HUB", PORTA_PADRAO_HUB),
        )


def origens_permitidas(ambiente: Mapping[str, str]) -> tuple[str, ...]:
    """Origens (sites) autorizadas a chamar a API pelo navegador, separadas por vírgula."""
    bruto = ambiente.get("HUB_RTC_ORIGENS_PERMITIDAS", "")
    return tuple(origem.strip() for origem in bruto.split(",") if origem.strip())
