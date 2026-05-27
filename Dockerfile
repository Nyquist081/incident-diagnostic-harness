FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY main.py ./
COPY data ./data
COPY prompts ./prompts
COPY scripts ./scripts
COPY src ./src

ENTRYPOINT ["uv", "run", "python", "main.py"]
