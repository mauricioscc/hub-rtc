"""Configuração do Hub lida das variáveis de ambiente.

Fica fora das camadas: só a composição (e os testes de fumaça) a usam.
"""

from collections.abc import Mapping
from dataclasses import dataclass

HOST_PADRAO = "localhost"
PORTA_PADRAO_REGIME_REGULAR = "8081"
PORTA_PADRAO_SIMPLES_NACIONAL = "8082"
PORTA_PADRAO_GERADOR_DANFSE = "8083"


@dataclass(frozen=True)
class EnderecosMotores:
    """URLs base dos três motores oficiais da Receita Federal."""

    regime_regular: str
    simples_nacional: str
    gerador_danfse: str

    @classmethod
    def do_ambiente(cls, ambiente: Mapping[str, str]) -> "EnderecosMotores":
        host = ambiente.get("HUB_RTC_HOST", HOST_PADRAO)

        def url(variavel_da_porta: str, porta_padrao: str) -> str:
            return f"http://{host}:{ambiente.get(variavel_da_porta, porta_padrao)}"

        return cls(
            regime_regular=url("PORTA_REGIME_REGULAR", PORTA_PADRAO_REGIME_REGULAR),
            simples_nacional=url("PORTA_SIMPLES_NACIONAL", PORTA_PADRAO_SIMPLES_NACIONAL),
            gerador_danfse=url("PORTA_GERADOR_DANFSE", PORTA_PADRAO_GERADOR_DANFSE),
        )
