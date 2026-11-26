"""Endereços dos motores oficiais, lidos do ambiente.

O mesmo código precisa apontar para o Docker local (desenvolvimento)
e para o servidor Docker da empresa (produção), mudando só variáveis.
"""

from hub_rtc.configuracao import EnderecosMotores


def test_sem_variaveis_aponta_para_o_docker_local() -> None:
    enderecos = EnderecosMotores.do_ambiente({})

    assert enderecos.regime_regular == "http://localhost:8081"
    assert enderecos.simples_nacional == "http://localhost:8082"
    assert enderecos.gerador_danfse == "http://localhost:8083"


def test_host_e_portas_do_servidor_da_empresa_vem_do_ambiente() -> None:
    ambiente = {
        "HUB_RTC_HOST": "docker.empresa.local",
        "PORTA_REGIME_REGULAR": "9081",
        "PORTA_SIMPLES_NACIONAL": "9082",
        "PORTA_GERADOR_DANFSE": "9083",
    }

    enderecos = EnderecosMotores.do_ambiente(ambiente)

    assert enderecos.regime_regular == "http://docker.empresa.local:9081"
    assert enderecos.simples_nacional == "http://docker.empresa.local:9082"
    assert enderecos.gerador_danfse == "http://docker.empresa.local:9083"
