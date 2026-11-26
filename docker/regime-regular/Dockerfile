# Calculadora RTC - Regime Regular (Receita Federal), compilada da tag oficial.
# Nenhuma linha do código da Receita é alterada (ver docs/adr/ADR001).

# Imagem oficial do Maven 3.9 (a mesma linha do wrapper da Receita): o
# repositório não versiona o maven-wrapper.jar, então ./mvnw não roda aqui.
FROM maven:3.9-eclipse-temurin-25 AS compilacao
ARG VERSAO_REGIME_REGULAR
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /fonte
RUN git clone --depth 1 --branch "${VERSAO_REGIME_REGULAR}" \
    https://github.com/ReceitaFederal/calculadora-rtc-regime-regular.git .
RUN mvn -q clean package -DskipTests --batch-mode \
    && cp target/api-regime-geral.jar /app.jar

FROM eclipse-temurin:25-jre
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=compilacao /app.jar ./api-regime-geral.jar
# O banco oficial chega por volume em /app/calculadora/db.
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-Dspring.profiles.active=offline", "-jar", "api-regime-geral.jar"]
