FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN groupadd --system pcf && useradd --system --gid pcf --home-dir /app pcf
COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
RUN pip install --no-cache-dir .
RUN mkdir -p /app/data/objects && chown -R pcf:pcf /app

USER pcf

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
