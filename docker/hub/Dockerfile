# Hub RTC (API FastAPI + tela web), construído a partir da raiz do repositório.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
RUN useradd --system --no-create-home hub
USER hub
EXPOSE 8000
CMD ["uvicorn", "hub_rtc.composicao:criar_aplicacao", "--factory", "--host", "0.0.0.0", "--port", "8000"]
