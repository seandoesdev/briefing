# syntax=docker/dockerfile:1.7

# ---------- Builder ----------
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# kiwipiepy 빌드에 gcc/g++ 필요할 수 있음. wheel이 있으면 빠르게 끝남.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install deps first (cache layer)
COPY pyproject.toml ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install \
        "fastapi>=0.110" \
        "uvicorn[standard]>=0.27" \
        "jinja2>=3.1" \
        "python-multipart>=0.0.9" \
        "pydantic>=2.6" \
        "pydantic-settings>=2.2" \
        "kiwipiepy>=0.17" \
        "GitPython>=3.1"

# Install the package itself (non-editable: copies into site-packages so /build can be discarded)
COPY src ./src
COPY README.md ./
RUN /opt/venv/bin/pip install --no-deps .

# ---------- Runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# git: GitVaultSync 가 런타임에 git 명령을 호출함.
# openssh-client: git push over SSH 시 필요.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        openssh-client \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --system briefing && useradd --system --gid briefing --home /app --shell /usr/sbin/nologin briefing

WORKDIR /app

# Bring venv (deps + briefing package installed into site-packages)
COPY --from=builder /opt/venv /opt/venv

# Static assets and data files
COPY data /app/data

# Entrypoint helper
COPY docker/entrypoint.sh /usr/local/bin/briefing-entrypoint
RUN chmod +x /usr/local/bin/briefing-entrypoint

# Runtime dirs (mounted as volumes in compose; created here so chown works at build time)
RUN mkdir -p /app/vault /app/runtime \
    && chown -R briefing:briefing /app

USER briefing

EXPOSE 8000

# Defaults — can be overridden via env.
ENV BRIEFING_DB_PATH=/app/runtime/briefing.db \
    BRIEFING_LOG_PATH=/app/runtime/briefing.log \
    BRIEFING_VAULT_PATH=/app/vault \
    BRIEFING_STOPWORDS_PATH=/app/data/stopwords.txt

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, sys; \
                   r = urllib.request.urlopen('http://127.0.0.1:8000/admin', timeout=3); \
                   sys.exit(0 if r.status in (200, 401) else 1)" \
        || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/briefing-entrypoint"]
CMD ["uvicorn", "briefing.interface.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
