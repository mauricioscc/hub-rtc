"""Único ponto que liga portas a adaptadores.

Uso: uvicorn hub_rtc.composicao:criar_aplicacao --factory
"""

import os

import httpx
from fastapi import FastAPI

from hub_rtc.adaptadores.motor_regime_regular import MotorRegimeRegular
from hub_rtc.casos_de_uso.calcular_regime_regular import CalcularRegimeRegular
from hub_rtc.casos_de_uso.consultar_situacoes_tributarias import ConsultarSituacoesTributarias
from hub_rtc.configuracao import EnderecosMotores, origens_permitidas
from hub_rtc.entrada.api import criar_app

TEMPO_LIMITE_MOTOR_SEGUNDOS = 30


def criar_aplicacao() -> FastAPI:
    enderecos = EnderecosMotores.do_ambiente(os.environ)
    cliente = httpx.Client(base_url=enderecos.regime_regular, timeout=TEMPO_LIMITE_MOTOR_SEGUNDOS)
    motor = MotorRegimeRegular(cliente)
    return criar_app(
        CalcularRegimeRegular(motor),
        ConsultarSituacoesTributarias(motor),
        origens_permitidas(os.environ),
    )
