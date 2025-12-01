#
# Multi-stage build
#

# -- Stage 1 - prepare

FROM python:3.13-slim AS builder
LABEL "maintainer"="ICTU DevOps"

# Fix https://stackoverflow.com/questions/69692842/error-message-error0308010cdigital-envelope-routinesunsupported
# ENV NODE_OPTIONS "--openssl-legacy-provider"

# The installer requires curl (and certificates) to download the release archive
# Also install libpq-dev for psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    make \
    git \
    libpq-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for pyright)
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs

# Download uv installer
ADD https://astral.sh/uv/0.5.4/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Ensure that all uv commands compile bytecode
ENV UV_COMPILE_BYTECODE=1

# Always use the latest pyright version
ENV PYRIGHT_PYTHON_FORCE_VERSION="latest"

# Install pyright globally
RUN npm install -g pyright

# Install packages
WORKDIR /api
COPY ./pyproject.toml ./uv.lock /api/

# Do not use venv
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
# Increase HTTP timeout for slow network connections
ENV UV_HTTP_TIMEOUT=300
RUN uv sync --frozen --no-install-project

# Run pyright once, it requires node. This will prevent installation of node during pipeline.
WORKDIR /app
RUN pyright

# -- Stage 2 - package (final image with build artifacts and without source code)

FROM library/python:3.13-slim

# Pass IMAGE_TAG (injected from build environment/pipeline)
ARG IMAGE_TAG
ENV IMAGE_TAG=${IMAGE_TAG}

WORKDIR /backend

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download uv installer
ADD https://astral.sh/uv/0.5.4/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY ./alembic.ini /backend/alembic.ini
COPY ./alembic /backend/alembic
COPY ./app /backend/app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --no-server-header"]
