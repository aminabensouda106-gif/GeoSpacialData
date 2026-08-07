FROM python:3.12-slim

WORKDIR /app

COPY apps/api/pyproject.toml ./pyproject.toml
COPY apps/api/platform_api ./platform_api

RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache -e .

COPY recipes ./recipes

ENV PLATFORM_REPO_ROOT=/app

EXPOSE 8000

CMD ["uvicorn", "platform_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
