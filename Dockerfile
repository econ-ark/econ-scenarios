FROM python:3.13-slim
# git for the pinned HARK dependency.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /remark
COPY . .
RUN uv sync --frozen
CMD ["./reproduce.sh"]
