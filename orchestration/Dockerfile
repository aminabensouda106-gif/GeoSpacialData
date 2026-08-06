FROM python:3.12-slim

WORKDIR /opt/dagster/app

COPY pyproject.toml .
COPY platform_orchestration ./platform_orchestration

RUN pip install --no-cache-dir -e .

COPY dagster.yaml /opt/dagster/dagster_home/dagster.yaml
ENV DAGSTER_HOME=/opt/dagster/dagster_home

EXPOSE 3000

CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000", "-m", "platform_orchestration.definitions"]
