# Gera o banco oficial SQLite (calculadora-pro.db) a partir dos scripts
# Flyway publicados pela Receita no repositório do Regime Regular.
# O mesmo banco é usado pelas duas calculadoras (somente leitura).

# Imagem oficial do Maven 3.9 (a mesma linha do wrapper da Receita): o
# repositório não versiona o maven-wrapper.jar, então ./mvnw não roda aqui.
FROM maven:3.9-eclipse-temurin-25 AS gerador
ARG VERSAO_REGIME_REGULAR
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /fonte
RUN git clone --depth 1 --branch "${VERSAO_REGIME_REGULAR}" \
    https://github.com/ReceitaFederal/calculadora-rtc-regime-regular.git .
RUN mkdir -p calculadora/db \
    && mvn -q flyway:migrate -Dflyway.configFiles=./flyway/flyway-pro.conf --batch-mode --errors \
    && test -s calculadora/db/calculadora-pro.db

FROM alpine:3.22
COPY --from=gerador /fonte/calculadora/db/calculadora-pro.db /banco-gerado/calculadora-pro.db
# Ao subir, copia o banco para o volume compartilhado e encerra.
CMD ["sh", "-c", "cp /banco-gerado/calculadora-pro.db /banco/calculadora-pro.db && echo 'banco oficial pronto'"]
