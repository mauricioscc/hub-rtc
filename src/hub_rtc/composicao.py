"""Único ponto que liga portas a adaptadores.

Uso: uvicorn hub_rtc.composicao:criar_aplicacao --factory
"""

import os

import httpx
from fastapi import FastAPI

from hub_rtc.adaptadores.motor_regime_regular import MotorRegimeRegular
from hub_rtc.adaptadores.motor_simples_nacional import MotorSimplesNacional
from hub_rtc.casos_de_uso.calcular_regime_regular import CalcularRegimeRegular
from hub_rtc.casos_de_uso.calcular_simples_nacional import CalcularSimplesNacional
from hub_rtc.casos_de_uso.consultar_atividades_simples import ConsultarAtividadesSimples
from hub_rtc.casos_de_uso.consultar_situacoes_tributarias import ConsultarSituacoesTributarias
from hub_rtc.configuracao import EnderecosMotores, origens_permitidas
from hub_rtc.entrada.api import criar_app, criar_roteador_regime_regular
from hub_rtc.entrada.api_simples import criar_roteador_simples

TEMPO_LIMITE_MOTOR_SEGUNDOS = 30


def _cliente(endereco: str) -> httpx.Client:
    return httpx.Client(base_url=endereco, timeout=TEMPO_LIMITE_MOTOR_SEGUNDOS)


def criar_aplicacao() -> FastAPI:
    enderecos = EnderecosMotores.do_ambiente(os.environ)
    regime_regular = MotorRegimeRegular(_cliente(enderecos.regime_regular))
    simples_nacional = MotorSimplesNacional(_cliente(enderecos.simples_nacional))
    roteadores = [
        criar_roteador_regime_regular(
            CalcularRegimeRegular(regime_regular),
            ConsultarSituacoesTributarias(regime_regular),
        ),
        criar_roteador_simples(
            CalcularSimplesNacional(simples_nacional),
            ConsultarAtividadesSimples(simples_nacional),
        ),
    ]
    return criar_app(roteadores, origens_permitidas(os.environ))
