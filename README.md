# Hub RTC

Ferramenta interna que reúne, num só lugar, as três ferramentas oficiais da Receita
Federal para a Reforma Tributária do Consumo (CBS, IBS e Imposto Seletivo, LC 214/2025):

| Motor | Versão | Porta | Repositório |
| --- | --- | --- | --- |
| Calculadora Regime Regular | 1.7.2 | 8081 | [calculadora-rtc-regime-regular](https://github.com/ReceitaFederal/calculadora-rtc-regime-regular) |
| Calculadora Simples Nacional | 1.0.2 | 8082 | [calculadora-rtc-simples-nacional](https://github.com/ReceitaFederal/calculadora-rtc-simples-nacional) |
| Gerador de DANFSe | 1.0.0 | 8083 | [calculadora-rtc-gerador-danfse](https://github.com/ReceitaFederal/calculadora-rtc-gerador-danfse) |

> Os resultados são simulações feitas com os motores oficiais. Não substituem a
> emissão nem a autorização de documentos fiscais.

## Estado atual: Fase 1 (cálculo do Regime Regular)

O Hub calcula CBS, IBS e Imposto Seletivo pelo motor Regime Regular, por API
(`POST /api/calculos/regime-regular`) e por uma tela web. Simples Nacional e
DANFSe chegam nas próximas fases. Ainda não há `aliquotasNominais` (o motor as
exige para fatos geradores a partir de 01/01/2027).

## Subir o Hub e os motores

Requisito: Docker com Compose. Java, Maven e Go **não** são necessários.

```bash
cp .env.example .env
docker compose up -d --build --wait
```

O primeiro build leva alguns minutos (baixa dependências e gera o banco).
Com tudo no ar, a tela e a API do Hub ficam em <http://localhost:8000>
(docs da API em `/docs`). Swagger de cada motor:

- Regime Regular: <http://localhost:8081/api/swagger-ui.html>
- Simples Nacional: <http://localhost:8082/api/swagger-ui.html>
- Gerador de DANFSe: <http://localhost:8083/api/swagger-ui/index.html>

Para atualizar um motor, troque a versão no `.env` e rode
`docker compose up -d --build` (ver [ADR003](docs/adr/ADR003-versoes-fixadas-e-banco-gerado-em-conteiner.md)).

## Tela de testes no GitHub Pages

O Pages só serve arquivos estáticos: ele hospeda a **tela**, não a API nem os motores.
Para o funcionário testar:

1. No servidor Docker da empresa, no `.env`, defina
   `HUB_RTC_ORIGENS_PERMITIDAS=https://<usuario>.github.io` e rode `docker compose up -d --build`.
   O Hub precisa estar acessível a quem vai testar (endereço HTTPS público ou VPN).
2. No GitHub: *Settings → Pages → Source: GitHub Actions*. O workflow
   [pages.yml](.github/workflows/pages.yml) publica a tela a cada mudança em `src/hub_rtc/entrada/web/`.
3. O funcionário abre `https://<usuario>.github.io/<repositorio>/`, informa o endereço do
   Hub uma vez (fica lembrado no navegador) ou usa `?api=https://endereco-do-hub`.

Endereço atual dos testes: tela em <https://mauricioscc.github.io/hub-rtc/>, Hub em
`https://office-mscx.tailbf5033.ts.net`, publicado pelo Tailscale Funnel a partir do PC
do desenvolvedor (`tailscale funnel --bg 8000`; para desligar: `tailscale funnel --https=443 off`).
O Hub só responde enquanto esse PC e o Docker estiverem ligados.

Sem Pages, basta abrir o endereço do próprio Hub: ele serve a mesma tela.

## Desenvolvimento

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"   # Linux: .venv/bin/pip

pytest              # testes de unidade (rápidos, sem Docker)
pytest -m fumaca    # testa os motores no ar (Docker local)
ruff check . && ruff format --check .
mypy src tests
lint-imports        # garante que as camadas não se misturam
```

Para testar o servidor Docker da empresa em vez do local:
`HUB_RTC_HOST=<endereco-do-servidor> pytest -m fumaca`.

## Arquitetura

```
src/hub_rtc/
  dominio/        entidades e regras, sem I/O
  portas/         interfaces (Protocol) que os casos de uso exigem
  casos_de_uso/   um caso de uso por arquivo
  adaptadores/    clientes HTTP dos três motores
  entrada/        rotas FastAPI e tela web
  composicao.py   único ponto que liga portas a adaptadores
```

Dependências só apontam para dentro (camadas de baixo não conhecem as de cima).
Decisões registradas em [docs/adr](docs/adr).
